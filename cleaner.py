"""
DataCleaner — Pandas-based cleaning with per-step reporting.
"""

import re
import logging
from typing import Optional

import numpy as np
import pandas as pd
from tqdm import tqdm

logger = logging.getLogger("pipeline.cleaner")


class DataCleaner:
    def __init__(self, config):
        self.config = config

    def _detect_text_columns(self, df: pd.DataFrame) -> list[str]:
        """Heuristic: columns where avg string length > 20."""
        text_cols = []
        for col in df.select_dtypes(include=["object", "string"]).columns:
            avg_len = df[col].dropna().astype(str).str.len().mean()
            if avg_len and avg_len > 20:
                text_cols.append(col)
        return text_cols or list(df.select_dtypes(include=["object", "string"]).columns)

    def clean(self, df: pd.DataFrame, pbar: Optional[tqdm] = None) -> tuple[pd.DataFrame, dict]:
        df = df.copy()
        report = {
            "original_rows": len(df),
            "original_cols": len(df.columns),
            "dropped_all_null": 0,
            "dropped_duplicates": 0,
            "dropped_short_text": 0,
            "numeric_nulls_filled": 0,
            "text_nulls_filled": 0,
            "final_rows": 0,
        }

        # Step 1 — Drop fully null rows
        before = len(df)
        df = df.dropna(how="all")
        report["dropped_all_null"] = before - len(df)
        if pbar:
            pbar.update(report["dropped_all_null"])

        # Step 2 — Strip whitespace from true string columns (skip bool/mixed)
        str_cols = df.select_dtypes(include=["object"]).columns
        for col in str_cols:
            try:
                # Only strip if column actually contains strings
                if df[col].dropna().apply(lambda x: isinstance(x, str)).any():
                    df[col] = df[col].apply(lambda x: x.strip() if isinstance(x, str) else x)
            except Exception:
                pass

        # Step 3 — Replace empty strings with NaN
        for col in str_cols:
            try:
                df[col] = df[col].replace(r"^\s*$", np.nan, regex=True)
            except Exception:
                pass

        # Step 4 — Fill numeric NaN
        num_cols = df.select_dtypes(include=np.number).columns
        for col in num_cols:
            null_count = df[col].isna().sum()
            if null_count > 0:
                strategy = self.config.fill_numeric_na
                if strategy == "mean":
                    df[col] = df[col].fillna(df[col].mean())
                elif strategy == "median":
                    df[col] = df[col].fillna(df[col].median())
                else:
                    df[col] = df[col].fillna(0)
                report["numeric_nulls_filled"] += null_count
        if pbar:
            pbar.update(min(len(num_cols) * 10, len(df) // 4))

        # Step 5 — Fill text NaN with empty string, then drop short rows
        text_cols = self.config.text_columns or self._detect_text_columns(df)
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].fillna("")
                report["text_nulls_filled"] += df[col].eq("").sum()

        # Step 6 — Drop rows where all text cols are too short
        if text_cols:
            valid_text = df[text_cols].astype(str).apply(
                lambda col: col.str.len() >= self.config.min_text_length
            ).any(axis=1)
            before = len(df)
            df = df[valid_text].copy()
            report["dropped_short_text"] = before - len(df)

        # Step 7 — Drop duplicates
        if self.config.drop_duplicate_rows:
            before = len(df)
            df = df.drop_duplicates()
            report["dropped_duplicates"] = before - len(df)
            if pbar:
                pbar.update(report["dropped_duplicates"])

        # Step 8 — Normalize text: collapse whitespace
        for col in text_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(r"\s+", " ", regex=True).str.strip()

        df = df.reset_index(drop=True)
        report["final_rows"] = len(df)

        if pbar:
            remaining = report["original_rows"] - pbar.n
            if remaining > 0:
                pbar.update(remaining)

        logger.info(
            f"Cleaning: {report['original_rows']} → {report['final_rows']} rows "
            f"(dropped {report['original_rows'] - report['final_rows']} rows)"
        )
        return df, report
