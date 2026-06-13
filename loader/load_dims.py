"""
load_dims.py
------------------------------------------------------------
Dimension refresh load — truncates and reloads staging.dim_customer,
staging.dim_product, staging.dim_territory from /data/. Fact tables
(fact_sales, fact_returns) are not touched.

Use this after editing the dimension lookup CSVs in /data/ (e.g. to
simulate SCD2 attribute changes for dim_customer/dim_product). Snapshots
must run before dbt run so the SCD2 diff is captured:

    1. Edit AdventureWorks Customer/Product/Territory Lookup.csv in /data/
    2. python loader/load_dims.py
       (this also triggers dbt snapshot, then dbt run)
"""

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

logger = get_logger("load_dims")

DATA_PATH = os.getenv("DATA_PATH", "./data")

# staging table -> (source CSV filename, date columns to parse)
TABLES = {
    "dim_customer": ("AdventureWorks Customer Lookup.csv", ["BirthDate"]),
    "dim_product": ("AdventureWorks Product Lookup.csv", None),
    "dim_territory": ("AdventureWorks Territory Lookup.csv", None),
}


def trigger_dbt_snapshot() -> None:
    """Run `dbt snapshot` from the dbt/ project directory."""
    dbt_dir = ROOT_DIR / "dbt"
    try:
        result = subprocess.run(
            ["dbt", "snapshot"], cwd=dbt_dir, capture_output=True, text=True, check=True
        )
        logger.info(result.stdout)
    except FileNotFoundError:
        logger.error("dbt executable not found — skipping dbt snapshot")
    except subprocess.CalledProcessError as exc:
        logger.error(f"dbt snapshot failed:\n{exc.stdout}\n{exc.stderr}")


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


def run_dims_load() -> None:
    engine = get_engine()
    batch_id = generate_batch_id()
    loaded_at = datetime.now()

    logger.info(f"Starting dimension load — batch_id={batch_id}")

    summary = []
    for table_name, (csv_file, date_columns) in TABLES.items():
        filepath = os.path.join(DATA_PATH, csv_file)
        validate_file_exists(filepath)

        started_at = datetime.now()
        df = read_csv(filepath, date_columns=date_columns)
        df["loaded_at"] = loaded_at
        df["batch_id"] = batch_id

        with engine.begin() as conn:
            conn.exec_driver_sql(f"TRUNCATE TABLE staging.{table_name}")
            df.to_sql(table_name, conn, schema="staging", if_exists="append", index=False)
        finished_at = datetime.now()

        logger.info(f"Loaded {len(df)} rows into staging.{table_name}")
        log_table_load(engine, batch_id, "dims", table_name, filepath, len(df), started_at, finished_at)
        summary.append((table_name, len(df)))

    logger.info("Dimension load complete")
    log_run_summary(logger, "Dimension load", batch_id, summary)
    trigger_dbt_snapshot()
    trigger_dbt_run()


if __name__ == "__main__":
    run_dims_load()
