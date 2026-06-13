# AdventureWorks Analytics — CLAUDE.md

## Start Every Session Here

Read these files in order before doing anything:

1. `CLAUDE-PROGRESS.txt` — find current phase and first unchecked [ ] task
2. `docs/architecture.md` — understand design decisions before writing any code
3. `docs/data_dictionary.md` — column names, types, and SCD rules before writing any SQL
4. The specific file you are about to edit — always read before writing

After reading, state:
- What phase you are in
- What the next task is
- Any blockers noted in CLAUDE-PROGRESS.txt

When a task is complete, mark it [DONE] in CLAUDE-PROGRESS.txt and update the header
(Last updated, Last session, Current phase) before ending the session.

---

## Project Overview

End-to-end analytics engineering project simulating a retail/supply chain data warehouse.
Source data is treated as D365 exports — clean, structured, no medallion layer needed.
Two schemas: `staging` (raw land) → `mart` (star schema). Power BI connects to `mart` only.

---

## Tech Stack

| Layer | Tool |
|---|---|
| Source | CSV files in `/data/` |
| Database | PostgreSQL 15 (local via Docker) |
| Transformation | dbt (staging views → mart tables + snapshots) |
| Orchestration | Apache Airflow + Docker Compose |
| Visualisation | Power BI Desktop → Power BI Service |
| Language | Python 3.11, SQL |

---

## Project Structure

```
adventureworks-analytics/
├── CLAUDE.md               ← you are here
├── CLAUDE-PROGRESS.txt     ← read this first every session
├── data/                   ← source CSV files — do not modify
├── database/               ← PostgreSQL DDL — run in order (01, 02, 03)
├── loader/                 ← load_full.py, load_incremental.py
├── utils/                  ← db_connection.py, logger.py, file_utils.py
├── logs/                   ← runtime logs — gitignored
├── dbt/
│   ├── models/
│   │   ├── staging/        ← stg_ prefix, views, 1:1 with source
│   │   ├── mart/           ← dim_ fact_ prefix, tables
│   │   └── utils/          ← dim_calendar (generated, not source-conformed)
│   ├── snapshots/          ← SCD Type 2 via dbt snapshot
│   ├── seeds/              ← static dims: dim_product_category, dim_product_subcategory
│   ├── tests/              ← custom SQL data quality tests
│   └── macros/             ← generate_schema_name.sql, generate_surrogate_key.sql
├── airflow/                ← Dockerfile, docker-compose.yml, dags/
├── powerbi/                ← AdventureWorks.pbix, dax_measures.md, rls_setup.md
└── docs/
    ├── architecture.md     ← design decisions and ADRs
    ├── data_dictionary.md  ← all tables, columns, types, SCD rules
    ├── business_questions.md
    └── erd.png
```

---

## Key Conventions

### SQL / dbt
- Staging models: always `materialized='view'`
- Mart models: always `materialized='table'` or `materialized='incremental'`
- Fact tables: hash surrogate key `md5(cast(natural_key as varchar))`
- Dim tables: integer surrogate key, generated via `row_number()` in mart models (see ADR-009)
- SCD Type 2: use `dbt snapshot` — never manually manage history in mart models
- Static dims (<50 rows): live in `dbt/seeds/`, loaded via `dbt seed`
- Always use `{{ ref() }}` — never hardcode schema names
- `dim_calendar` lives in `models/utils/` — generated, not source-conformed
- Always run in order: `dbt seed` → `dbt snapshot` → `dbt run` → `dbt test`
- `generate_schema_name.sql` must exist in macros before first `dbt run`

### Python
- Always import `utils.db_connection` — never define connections inline
- Always import `utils.logger` — never use bare `print()`
- Batch ID format: `YYYYMMDD_HHmmss` — generated once at script start
- `loaded_at` = `datetime.now()` set once per batch, not per row
- CSV encoding: `latin-1`
- CSV date format: `DD/MM/YYYY` — always parse with `dayfirst=True`

### PostgreSQL
- Two schemas only: `staging` and `mart`
- Python → `staging` only. dbt → `mart` only. Never cross these.
- Fact surrogate keys: `CHAR(32)` (md5 hash)
- Dim surrogate keys: `INT`, generated via `row_number()` in dbt mart models (see ADR-009)
- Every fact table has: surrogate PK, `loaded_at TIMESTAMP`, `batch_id VARCHAR(50)`
- Every SCD2 dim has: `scd_start_date`, `scd_end_date`, `scd_is_current`, `scd_version`

### Naming
- Staging models: `stg_{entity}` — e.g. `stg_sales`, `stg_customer`
- Mart facts: `fact_{entity}` — e.g. `fact_sales`, `fact_returns`
- Mart dims: `dim_{entity}` — e.g. `dim_customer`, `dim_product`
- Snapshots: `snap_{entity}` — e.g. `snap_customer`, `snap_product`
- Seeds: match the mart dim name they feed

---

## Data Model — Grain

| Table | Grain | Surrogate Key |
|---|---|---|
| `fact_sales` | One row per order line item | `md5(OrderNumber + OrderLineItem + OrderDate)` (see ADR-010) |
| `fact_returns` | One row per (ReturnDate + TerritoryKey + ProductKey) | `md5(ReturnDate + TerritoryKey + ProductKey)` |
| `dim_customer` | One current row per customer (SCD2 adds versions) | INT IDENTITY |
| `dim_product` | One current row per product (SCD2 adds versions) | INT IDENTITY |
| `dim_territory` | One row per territory — static, 15 rows | INT IDENTITY |
| `dim_calendar` | One row per date 2020-01-01 to 2026-12-31 | Date (natural PK) |

---

## SCD Rules

| Dim | SCD Type 2 — track history | SCD Type 1 — overwrite |
|---|---|---|
| `dim_customer` | AnnualIncome, MaritalStatus, HomeOwner, Occupation | Prefix, EmailAddress, Gender, EducationLevel |
| `dim_product` | ProductCost, ProductPrice | ProductName, ProductDescription, ProductColor, ProductSize, ProductStyle |

---

## Incremental Load Logic

- Watermark: `loaded_at` on staging tables
- dbt strategy: `delete+insert` on surrogate key
- Idempotent: same batch re-run = no duplicates (surrogate key is deterministic md5)
- Full load: `load_full.py` — run once only to establish baseline
- Incremental: `load_incremental.py` — triggered nightly by Airflow

---

## Power BI

- Connection: Import mode — connects to `mart` schema only
- All DAX measures live in `_Measures` table — no columns, just measures
- Never create calculated columns where a measure will do
- RLS on `dim_territory[Continent]` and `dim_territory[Country]`
- Do not remove or rename any original source columns — additive only

---

## Git Workflow

- One feature branch + one PR per phase (e.g. `phase-3-dbt-models`).
- At the end of a phase, once all its tasks are marked `[DONE]` in
  `CLAUDE-PROGRESS.txt`: commit the changes, push the branch to `origin`, and
  open a PR against `main` summarising what was built and verified.
- Wait for the user to merge the PR before branching off `main` for the next
  phase.
- This is pre-authorized — commit/push/PR for phase wrap-up does not require
  asking first. Still ask before any destructive git operation (force-push,
  reset --hard, branch deletion, etc).

---

## Do Not

- Do not add medallion/bronze/silver layer — two schemas only
- Do not add `notebooks/` — data is from D365, no EDA needed
- Do not write directly to `mart` from Python
- Do not use `print()` — use `utils.logger`
- Do not hardcode connection strings — read from `.env` via `utils.db_connection`
- Do not snapshot static dims (territory, product_category, product_subcategory)
- Do not run `dbt run` before `generate_schema_name.sql` exists in macros
- Do not edit files in `/data/` — source CSVs are read-only
