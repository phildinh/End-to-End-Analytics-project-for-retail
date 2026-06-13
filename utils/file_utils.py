"""Shared file I/O helpers for the loader scripts."""

import os
from datetime import datetime

import pandas as pd


def validate_file_exists(filepath: str) -> None:
    """Raise FileNotFoundError if filepath does not exist."""
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Source file not found: {filepath}")


def read_csv(filepath: str, date_columns: list[str] | None = None) -> pd.DataFrame:
    """Read a source CSV — latin-1 encoding, DD/MM/YYYY dates."""
    validate_file_exists(filepath)
    return pd.read_csv(
        filepath,
        encoding="latin-1",
        parse_dates=date_columns,
        dayfirst=True,
    )


def generate_batch_id() -> str:
    """Return a batch identifier in YYYYMMDD_HHmmss format."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")
