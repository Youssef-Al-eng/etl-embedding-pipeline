#!/usr/bin/env python3
"""
Production-Grade Data Embedding Pipeline
Reads CSVs → Cleans → Chunks → Embeds via OpenAI API
Features: progress bars, error recovery, checkpointing, async batching
"""

import asyncio
import json
import logging
import os
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from tqdm import tqdm
from tqdm.asyncio import tqdm as atqdm

from config import PipelineConfig
from cleaner import DataCleaner
from checkpoint import CheckpointManager
from embedder import AsyncEmbedder
from reporter import PipelineReporter
import sys
sys.stdout.reconfigure(encoding='utf-8')
# ─── Logging Setup ────────────────────────────────────────────────────────────

def setup_logging(log_dir: str = "logs") -> logging.Logger:
    Path(log_dir).mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = f"{log_dir}/pipeline_{timestamp}.log"

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("pipeline"), log_file


# ─── Core Pipeline ────────────────────────────────────────────────────────────

class EmbeddingPipeline:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger, self.log_file = setup_logging(config.log_dir)
        self.cleaner = DataCleaner(config)
        self.checkpoint = CheckpointManager(config.checkpoint_dir)
        self.embedder = AsyncEmbedder(config)
        self.reporter = PipelineReporter()

    def discover_csv_files(self) -> list[Path]:
        """Find all CSV files in the data directory."""
        data_path = Path(self.config.data_dir)
        files = sorted(data_path.glob("**/*.csv"))
        self.logger.info(f"Discovered {len(files)} CSV file(s) in '{data_path}'")
        return files

    def load_csv(self, path: Path) -> pd.DataFrame:
        """Load a CSV with error handling and basic validation."""
        try:
            df = pd.read_csv(path, on_bad_lines="skip", encoding="utf-8", low_memory=False)
            self.logger.info(f"Loaded '{path.name}': {len(df):,} rows × {len(df.columns)} cols")
            return df
        except UnicodeDecodeError:
            df = pd.read_csv(path, on_bad_lines="skip", encoding="latin-1", low_memory=False)
            self.logger.warning(f"Fell back to latin-1 for '{path.name}'")
            return df
        except Exception as e:
            self.logger.error(f"Failed to load '{path.name}': {e}")
            raise

    def chunk_records(self, records: list[str], batch_size: int) -> list[list[str]]:
        """Split records into batches."""
        return [records[i : i + batch_size] for i in range(0, len(records), batch_size)]

    async def process_file(self, path: Path) -> dict:
        """Full pipeline for a single CSV file."""
        file_id = hashlib.md5(str(path).encode()).hexdigest()[:8]
        stats = {"file": path.name, "rows_loaded": 0, "rows_clean": 0,
                 "batches_total": 0, "batches_done": 0, "errors": 0,
                 "embeddings_saved": 0, "skipped": False}

        self.reporter.file_start(path.name)

        # ── Load ──────────────────────────────────────────────────────────────
        with tqdm(total=1, desc=f"  📂 Loading    {path.name[:40]:<40}", unit="file",
                  bar_format="{l_bar}{bar:30}{r_bar}", colour="cyan", leave=False) as pbar:
            df = self.load_csv(path)
            stats["rows_loaded"] = len(df)
            pbar.update(1)

        # ── Clean ─────────────────────────────────────────────────────────────
        with tqdm(total=len(df), desc=f"  🧹 Cleaning   {path.name[:40]:<40}", unit="row",
                  bar_format="{l_bar}{bar:30}{r_bar}", colour="yellow", leave=False) as pbar:
            clean_df, cleaning_report = self.cleaner.clean(df, pbar)
            stats["rows_clean"] = len(clean_df)
            self.reporter.cleaning_report(path.name, cleaning_report)

        if clean_df.empty:
            self.logger.warning(f"No clean records in '{path.name}' — skipping.")
            stats["skipped"] = True
            return stats

        # ── Serialize to text ─────────────────────────────────────────────────
        records = clean_df.apply(
            lambda row: " | ".join(f"{k}: {v}" for k, v in row.items() if pd.notna(v)),
            axis=1,
        ).tolist()

        # ── Checkpoint resume ─────────────────────────────────────────────────
        done_batches = self.checkpoint.load(file_id)
        batches = self.chunk_records(records, self.config.batch_size)
        stats["batches_total"] = len(batches)

        pending = [(i, b) for i, b in enumerate(batches) if i not in done_batches]
        if len(done_batches) > 0:
            self.logger.info(
                f"Resuming '{path.name}': {len(done_batches)}/{len(batches)} batches already done"
            )
            self.reporter.resume_notice(path.name, len(done_batches), len(batches))

        # ── Embed ─────────────────────────────────────────────────────────────
        all_embeddings = []
        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def embed_batch_safe(idx: int, batch: list[str], pbar):
            async with semaphore:
                for attempt in range(1, self.config.max_retries + 1):
                    try:
                        embeddings = await self.embedder.embed(batch)
                        self.checkpoint.save(file_id, idx)
                        pbar.update(len(batch))
                        pbar.set_postfix(batch=f"{idx+1}/{len(batches)}", errors=stats["errors"])
                        return idx, embeddings
                    except Exception as e:
                        wait = self.config.retry_delay * (2 ** (attempt - 1))
                        self.logger.warning(
                            f"Batch {idx} attempt {attempt}/{self.config.max_retries} failed: {e}. Retrying in {wait}s"
                        )
                        stats["errors"] += 1
                        if attempt < self.config.max_retries:
                            await asyncio.sleep(wait)
                        else:
                            self.logger.error(f"Batch {idx} permanently failed after {self.config.max_retries} attempts")
                            pbar.update(len(batch))
                            return idx, None

        embed_bar_desc = f"  🚀 Embedding  {path.name[:40]:<40}"
        with tqdm(total=len(records), desc=embed_bar_desc, unit="rec",
                  bar_format="{l_bar}{bar:30}{r_bar}", colour="green", leave=False) as pbar:
            tasks = [embed_batch_safe(i, b, pbar) for i, b in pending]
            results = await asyncio.gather(*tasks)

        # Merge results
        result_map = {i: emb for i, emb in results if emb is not None}
        for i in range(len(batches)):
            if i in result_map:
                all_embeddings.extend(result_map[i])

        stats["batches_done"] = len([r for r in results if r[1] is not None])
        stats["embeddings_saved"] = len(all_embeddings)

        # ── Save output ───────────────────────────────────────────────────────
        if all_embeddings:
            out_path = Path(self.config.output_dir) / f"{path.stem}_embeddings.npy"
            np.save(out_path, np.array(all_embeddings))
            meta_path = Path(self.config.output_dir) / f"{path.stem}_meta.json"
            meta_path.write_text(json.dumps({
                "source_file": str(path),
                "rows": stats["rows_clean"],
                "embedding_dim": len(all_embeddings[0]) if all_embeddings else 0,
                "model": self.config.embedding_model,
                "created_at": datetime.now().isoformat(),
            }, indent=2))
            self.logger.info(
                f"Saved {len(all_embeddings):,} embeddings → '{out_path}'"
            )

        self.reporter.file_done(stats)
        return stats

    async def run(self):
        """Main entry point — process all CSVs."""
        start_time = time.time()
        self.reporter.pipeline_start(self.config)

        files = self.discover_csv_files()
        if not files:
            self.reporter.no_files_found(self.config.data_dir)
            return

        all_stats = []
        for file_path in files:
            try:
                stats = await self.process_file(file_path)
                all_stats.append(stats)
            except Exception as e:
                self.logger.error(f"Fatal error processing '{file_path.name}': {e}", exc_info=True)
                all_stats.append({"file": file_path.name, "fatal_error": str(e)})

        elapsed = time.time() - start_time
        self.reporter.pipeline_summary(all_stats, elapsed, self.log_file)
        self.checkpoint.clear_all()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from config import PipelineConfig
    config = PipelineConfig()
    pipeline = EmbeddingPipeline(config)
    asyncio.run(pipeline.run())
