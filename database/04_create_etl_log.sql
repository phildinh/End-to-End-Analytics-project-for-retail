-- ============================================================================
-- 04_create_etl_log.sql
-- ETL run log — one row per table per pipeline run (full or incremental).
-- Written by loader/load_full.py and loader/load_incremental.py via
-- utils/etl_log.py. Gives a queryable history of what loaded, how many
-- rows, and when — for monitoring/debugging the pipeline.
-- ============================================================================

CREATE TABLE staging.etl_log (
    log_id      SERIAL       PRIMARY KEY,
    batch_id    VARCHAR(50)  NOT NULL,
    load_type   VARCHAR(20)  NOT NULL,   -- 'full', 'incremental', or 'dims'
    table_name  VARCHAR(50)  NOT NULL,   -- e.g. 'fact_sales'
    source_file VARCHAR(255) NOT NULL,
    row_count   INT          NOT NULL,
    started_at  TIMESTAMP    NOT NULL,
    finished_at TIMESTAMP    NOT NULL,
    status      VARCHAR(20)  NOT NULL,   -- 'success' or 'failed'
    message     VARCHAR(500)
);
