"""
adventureworks_pipeline
------------------------------------------------------------
Nightly ELT pipeline:

    load_to_staging -> dbt_seed -> dbt_snapshot -> dbt_run -> dbt_test

Idempotent end to end: load_incremental.py only appends new rows to
staging, and dbt's delete+insert incremental strategy with
deterministic md5 surrogate keys means re-running the DAG never
produces duplicates in mart.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

PROJECT_DIR = "/opt/airflow/project"
DBT_DIR = f"{PROJECT_DIR}/dbt"

default_args = {
    "owner": "adventureworks",
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="adventureworks_pipeline",
    description="Nightly incremental load + dbt transform/test for the AdventureWorks mart",
    default_args=default_args,
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["adventureworks"],
) as dag:

    load_to_staging = BashOperator(
        task_id="load_to_staging",
        bash_command=f"python {PROJECT_DIR}/loader/load_incremental.py",
    )

    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"cd {DBT_DIR} && dbt seed",
    )

    dbt_snapshot = BashOperator(
        task_id="dbt_snapshot",
        bash_command=f"cd {DBT_DIR} && dbt snapshot",
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run",
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test",
    )

    load_to_staging >> dbt_seed >> dbt_snapshot >> dbt_run >> dbt_test
