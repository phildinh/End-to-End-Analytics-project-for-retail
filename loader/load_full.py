"""
load_full.py
------------------------------------------------------------
Full load — reads all source CSVs from /data/, truncates every
staging table, and loads a clean baseline into the staging schema.

Run once to establish the baseline:
    python loader/load_full.py
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from utils.db_connection import get_engine
from utils.file_utils import generate_batch_id, read_csv, validate_file_exists
from utils.logger import get_logger

logger = get_logger("load_full")

DATA_PATH = os.getenv("DATA_PATH", "./data")

# staging table -> (source CSV filename, date columns to parse)
TABLES = {
    "fact_sales": ("fact_sales_2020_2026.csv", ["OrderDate", "StockDate"]),
    "fact_returns": ("fact_returns_2020_2026.csv", ["ReturnDate"]),
    "dim_customer": ("AdventureWorks Customer Lookup.csv", ["BirthDate"]),
    "dim_product": ("AdventureWorks Product Lookup.csv", None),
    "dim_territory": ("AdventureWorks Territory Lookup.csv", None),
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


def run_full_load() -> None:
    engine = get_engine()
    batch_id = generate_batch_id()
    loaded_at = datetime.now()

    logger.info(f"Starting full load — batch_id={batch_id}")

    for table_name, (csv_file, date_columns) in TABLES.items():
        filepath = os.path.join(DATA_PATH, csv_file)
        validate_file_exists(filepath)

        df = read_csv(filepath, date_columns=date_columns)
        df["loaded_at"] = loaded_at
        df["batch_id"] = batch_id

        with engine.begin() as conn:
            conn.exec_driver_sql(f"TRUNCATE TABLE staging.{table_name}")
            df.to_sql(table_name, conn, schema="staging", if_exists="append", index=False)

        logger.info(f"Loaded {len(df)} rows into staging.{table_name}")

    logger.info("Full load complete")
    trigger_dbt_run()


if __name__ == "__main__":
    run_full_load()
