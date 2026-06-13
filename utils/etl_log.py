"""ETL run logging — records one row per table per pipeline run to
staging.etl_log, and logs a per-table row count summary at the end of
a run. Used by loader/load_full.py and loader/load_incremental.py.
"""

import logging
from datetime import datetime

from sqlalchemy.engine import Engine


def log_table_load(
    engine: Engine,
    batch_id: str,
    load_type: str,
    table_name: str,
    source_file: str,
    row_count: int,
    started_at: datetime,
    finished_at: datetime,
    status: str = "success",
    message: str | None = None,
) -> None:
    """Insert one row into staging.etl_log recording a table load."""
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            INSERT INTO staging.etl_log
                (batch_id, load_type, table_name, source_file, row_count,
                 started_at, finished_at, status, message)
            VALUES (%(batch_id)s, %(load_type)s, %(table_name)s, %(source_file)s,
                    %(row_count)s, %(started_at)s, %(finished_at)s, %(status)s, %(message)s)
            """,
            {
                "batch_id": batch_id,
                "load_type": load_type,
                "table_name": table_name,
                "source_file": source_file,
                "row_count": row_count,
                "started_at": started_at,
                "finished_at": finished_at,
                "status": status,
                "message": message,
            },
        )


def log_run_summary(
    logger: logging.Logger,
    label: str,
    batch_id: str,
    rows_by_table: list[tuple[str, int]],
) -> None:
    """Log a one-line-per-table summary of rows loaded this run."""
    logger.info(f"--- {label} summary (batch {batch_id}) ---")
    for table_name, row_count in rows_by_table:
        logger.info(f"  {table_name:<15}: {row_count:>6} rows")
    logger.info("-" * 40)
