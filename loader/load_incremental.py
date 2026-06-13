"""
load_incremental.py
------------------------------------------------------------
Incremental load — appends new rows to staging.fact_sales and
staging.fact_returns. No truncation; dbt deduplicates on the
surrogate key (order_sk / return_sk).

The fact_*_2020_2026.csv files are the full-load baseline only
(see load_full.py) — they are never read here.

Nightly run (default incremental batch files from /data/test/):
    python loader/load_incremental.py

Test run against a specific batch file:
    python loader/load_incremental.py --file data/test/fact_sales_incremental_duplicate.csv
    python loader/load_incremental.py --file data/test/some_returns_batch.csv --table fact_returns
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.db_connection import get_engine
from utils.etl_log import log_run_summary, log_table_load
from utils.file_utils import generate_batch_id, read_csv, validate_file_exists
from utils.logger import get_logger

logger = get_logger("load_incremental")

DATA_PATH = os.getenv("DATA_PATH", "./data")

# staging table -> (default incremental batch CSV filename, date columns to parse)
TABLES = {
    "fact_sales": ("test/fact_sales_incremental_today.csv", ["OrderDate", "StockDate"]),
    "fact_returns": ("test/fact_returns_incremental_today.csv", ["ReturnDate"]),
}


def trigger_dbt_run() -> None:
    """Run `dbt run` from the dbt/ project directory."""
    dbt_dir = ROOT_DIR / "dbt"
    try:
        result = subprocess.run(
            ["dbt", "run"], cwd=dbt_dir, capture_output=True, text=True, check=True
        )
        logger.info(result.stdout)
    except FileNotFoundError:
        logger.error("dbt executable not found — skipping dbt run")
    except subprocess.CalledProcessError as exc:
        logger.error(f"dbt run failed:\n{exc.stdout}\n{exc.stderr}")


def load_table(engine, table_name: str, filepath: str, loaded_at: datetime, batch_id: str) -> int:
    validate_file_exists(filepath)
    df = read_csv(filepath, date_columns=TABLES[table_name][1])
    df["loaded_at"] = loaded_at
    df["batch_id"] = batch_id

    started_at = datetime.now()
    df.to_sql(table_name, engine, schema="staging", if_exists="append", index=False)
    finished_at = datetime.now()

    logger.info(f"Appended {len(df)} rows into staging.{table_name} from {filepath}")
    log_table_load(engine, batch_id, "incremental", table_name, filepath, len(df), started_at, finished_at)
    return len(df)


def run_incremental_load(file_override: str | None = None, table_override: str = "fact_sales") -> None:
    engine = get_engine()
    batch_id = generate_batch_id()
    loaded_at = datetime.now()

    logger.info(f"Starting incremental load — batch_id={batch_id}")

    summary = []
    if file_override:
        rows = load_table(engine, table_override, file_override, loaded_at, batch_id)
        summary.append((table_override, rows))
    else:
        for table_name, (csv_file, _) in TABLES.items():
            rows = load_table(engine, table_name, os.path.join(DATA_PATH, csv_file), loaded_at, batch_id)
            summary.append((table_name, rows))

    logger.info("Incremental load complete")
    log_run_summary(logger, "Incremental load", batch_id, summary)
    trigger_dbt_run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Incremental loader for AdventureWorks staging tables")
    parser.add_argument("--file", help="Path to a single CSV to append (used for testing)")
    parser.add_argument(
        "--table",
        default="fact_sales",
        choices=list(TABLES.keys()),
        help="Staging table the --file maps to (default: fact_sales)",
    )
    args = parser.parse_args()
    run_incremental_load(file_override=args.file, table_override=args.table)
