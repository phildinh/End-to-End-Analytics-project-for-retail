"""
adventureworks_pipeline
------------------------------------------------------------
Nightly ELT pipeline:

    load_facts_incremental --\
                               >-- dbt_seed -> dbt_snapshot -> dbt_run -> dbt_test
    load_dims_full ----------/

- load_facts_incremental: appends new rows to staging.fact_sales /
  staging.fact_returns only (load_incremental.py).
- load_dims_full: truncates + reloads staging.dim_customer,
  staging.dim_product, staging.dim_territory from /data/ (load_dims.py).

Idempotent end to end: dbt_snapshot captures SCD2 changes for
dim_customer/dim_product, dbt_run rebuilds the incremental fact tables
via delete+insert on deterministic md5 surrogate keys — re-running the
DAG never produces duplicates in mart.
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

    load_facts_incremental = BashOperator(
        task_id="load_facts_incremental",
        bash_command=f"python {PROJECT_DIR}/loader/load_incremental.py",
    )

    load_dims_full = BashOperator(
        task_id="load_dims_full",
        bash_command=f"python {PROJECT_DIR}/loader/load_dims.py",
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

    [load_facts_incremental, load_dims_full] >> dbt_seed >> dbt_snapshot >> dbt_run >> dbt_test
