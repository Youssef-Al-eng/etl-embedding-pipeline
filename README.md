# ⚡ Embedding Pipeline

A production-grade data pipeline that reads CSV files, cleans the data, chunks it into batches, and sends it to the OpenAI Embeddings API — with progress bars, error recovery, resume-from-checkpoint, and async batching.

---

## Features

- **Auto CSV discovery** — drop any `.csv` into the `data/` folder and it gets picked up automatically
- **Smart data cleaning** — drops null rows, deduplicates, strips whitespace, fills numeric NAs, filters short text
- **Async batching** — concurrent embedding requests with configurable parallelism
- **Resume from checkpoint** — crashes mid-run? Re-run the same command and it picks up exactly where it left off
- **Retry with backoff** — failed batches are retried up to 3× with exponential backoff
- **Rich terminal UI** — color-coded progress bars per stage (load / clean / embed) powered by `rich` and `tqdm`
- **Demo mode** — runs without an API key using deterministic mock embeddings, great for testing
- **Structured output** — saves `.npy` embedding arrays + `.json` metadata files per CSV

---

## Project Structure

```
embedding_pipeline/
├── pipeline.py              # Main orchestrator
├── config.py                # All settings via environment variables
├── cleaner.py               # 8-step Pandas data cleaner
├── checkpoint.py            # JSON-backed batch checkpointing
├── embedder.py              # Async OpenAI client + mock fallback
├── reporter.py              # Rich terminal UI
├── generate_sample_data.py  # Generates 3 sample CSVs for testing
├── requirements.txt
├── run.sh                   # Convenience runner script
├── data/                    # Place your CSV files here
├── output/                  # Embeddings and metadata saved here
├── checkpoints/             # Auto-managed resume state
└── logs/                    # Timestamped log files
```

---

## Installation

**Requirements:** Python 3.10+

```bash
# Clone or download the project, then:
cd embedding_pipeline
pip install -r requirements.txt
```

**Dependencies:**

| Package | Purpose |
|---|---|
| `pandas` | Data loading and cleaning |
| `numpy` | Embedding array storage |
| `tqdm` | Per-stage progress bars |
| `rich` | Colored terminal UI and summary tables |
| `openai` | OpenAI Embeddings API client |

---

## Quick Start

```bash
# Step 1 — Generate sample data (creates 3 CSVs in data/)
python generate_sample_data.py

# Step 2 — Run in demo mode (no API key needed)
python pipeline.py
```

For real OpenAI embeddings:

```bash
export OPENAI_API_KEY=sk-your-key-here
python pipeline.py
```

Or use the convenience script:

```bash
chmod +x run.sh
./run.sh           # demo mode
./run.sh --live    # live OpenAI API
```

---

## Configuration

All settings are controlled via environment variables — no code changes needed.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | _(empty)_ | Your OpenAI API key. If unset, runs in demo mode |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI model to use |
| `DATA_DIR` | `data` | Folder to scan for CSV files |
| `OUTPUT_DIR` | `output` | Where embeddings and metadata are saved |
| `BATCH_SIZE` | `100` | Records per API request |
| `MAX_CONCURRENT` | `5` | Maximum parallel API requests |
| `MAX_RETRIES` | `3` | Retry attempts per failed batch |
| `RETRY_DELAY` | `1.0` | Base delay (seconds) for exponential backoff |
| `MIN_TEXT_LENGTH` | `10` | Minimum characters for a row to be kept |
| `DROP_DUPLICATES` | `true` | Whether to deduplicate rows |
| `FILL_NUMERIC_NA` | `mean` | Strategy for filling numeric nulls: `mean`, `median`, or `zero` |

Example — custom settings:

```bash
BATCH_SIZE=50 MAX_CONCURRENT=3 EMBEDDING_MODEL=text-embedding-3-large python pipeline.py
```

---

## What Happens When You Run It

The pipeline processes each CSV file through three stages:

### 1. Load
Reads the CSV with automatic encoding detection (UTF-8, falls back to latin-1). Logs row and column counts.

### 2. Clean
An 8-step cleaning process runs on every file:

1. Drop fully null rows
2. Strip leading/trailing whitespace from string columns
3. Replace empty strings with `NaN`
4. Fill numeric `NaN` values (mean / median / zero)
5. Fill text `NaN` values with empty string
6. Drop rows where all text columns are too short (below `MIN_TEXT_LENGTH`)
7. Drop duplicate rows
8. Normalize whitespace (collapse multiple spaces to one)

### 3. Embed
Records are serialized to text (`column: value | column: value ...`), split into batches, and sent to the OpenAI API concurrently. Each completed batch is checkpointed immediately to disk.

---

## Terminal Output

```
╭─────────────────────────────╮
│    ⚡ EMBEDDING PIPELINE    │
╰─ model: text-embedding-3-small ─╯
  Data dir:   data
  Output  :   output
  Mode    :   DEMO MODE

▶ customers.csv
  📂 Loading    customers.csv   ████████████████████  1/1
  🧹 Cleaning   customers.csv   ████████████████████  303 rows
  Cleaning: 303 → 300 rows (dropped 3 = 1.0%)
  🚀 Embedding  customers.csv   ████████████████████  300/300  batch=3/3
  Result: ✓ Done   embeddings: 300

──────────────── Pipeline Complete ────────────────

  File              Rows (clean)   Embeddings   Errors   Status
  ──────────────────────────────────────────────────────────────
  customers.csv          300          300          0       ✓
  products.csv           500          500          0       ✓
  reviews.csv            400          400          0       ✓

  Files: 3/3   Rows: 1,200   Embeddings: 1,200   Time: 0m 2s
```

---

## Output Files

After a successful run, the `output/` folder contains:

```
output/
├── customers_embeddings.npy   # NumPy float32 array, shape (300, 1536)
├── customers_meta.json        # Source info, row count, model, timestamp
├── products_embeddings.npy    # shape (500, 1536)
├── products_meta.json
├── reviews_embeddings.npy     # shape (400, 1536)
└── reviews_meta.json
```

Load embeddings in Python:

```python
import numpy as np

embeddings = np.load("output/products_embeddings.npy")
print(embeddings.shape)   # (500, 1536)
print(embeddings[0])      # First embedding vector
```

---

## Resume After a Crash

If the pipeline is interrupted mid-run (network error, API timeout, `Ctrl+C`), just re-run the same command:

```bash
python pipeline.py
```

You will see:

```
⚡ Resuming 'products.csv': 3/5 batches already completed
```

Completed batches are skipped automatically. Checkpoint files are stored in `checkpoints/` and are cleared automatically after a fully successful run.

---

## Using Your Own CSV Files

1. Place any `.csv` file in the `data/` folder
2. Run `python pipeline.py`

No configuration needed. The pipeline automatically detects which columns contain text (columns where the average string length exceeds 20 characters) and uses those for embeddings. All other columns are included as metadata in the serialized record text.

---

## Demo Mode vs Live Mode

| | Demo Mode | Live Mode |
|---|---|---|
| Requires API key | No | Yes |
| Embeddings | Deterministic random vectors | Real OpenAI vectors |
| Output shape | `(N, 1536)` — same as `text-embedding-3-small` | `(N, 1536)` or `(N, 3072)` depending on model |
| Cost | Free | OpenAI API pricing applies |
| Use for | Development, testing, CI | Production |

---

## Logs

Every run writes a timestamped log file to `logs/`:

```
logs/pipeline_20260524_143021.log
```

The log contains every step — files discovered, row counts, batch completions, retries, errors, and the final summary. Useful for debugging or auditing past runs.

---

## Troubleshooting

**`ModuleNotFoundError`** — run `pip install -r requirements.txt`

**`AuthenticationError` from OpenAI** — check that `OPENAI_API_KEY` is exported correctly in your shell session

**Pipeline is slow** — increase `MAX_CONCURRENT` (try 10–20) and `BATCH_SIZE` (try 200–500) if your API tier allows it

**Rows being dropped unexpectedly** — lower `MIN_TEXT_LENGTH` in config, or set `DROP_DUPLICATES=false`

**Output embeddings look wrong** — verify the model name in `EMBEDDING_MODEL`; `text-embedding-3-large` produces `(N, 3072)` vectors instead of `(N, 1536)`