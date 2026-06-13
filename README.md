# AdventureWorks Analytics — End-to-End Retail Data Platform

An end-to-end analytics engineering project simulating a retail/supply chain data
warehouse for AdventureWorks Bike Shop, treated as a Microsoft Dynamics 365 export.

## What this project does

- Loads CSV "source" data (sales, returns, customers, products, territories) into a
  PostgreSQL `staging` schema via a Python loader
- Transforms staging data into a tested star schema in a `mart` schema using dbt,
  including SCD Type 2 history for customer and product dimensions
- Orchestrates the full pipeline nightly with Apache Airflow in Docker
- Serves the `mart` schema to a Power BI report with DAX measures and row-level security

## Tech stack

| Layer | Tool |
|---|---|
| Source | CSV files in `/data/` |
| Database | PostgreSQL 15 (local via Docker) |
| Transformation | dbt (staging views → mart tables + snapshots) |
| Orchestration | Apache Airflow + Docker Compose |
| Visualisation | Power BI Desktop → Power BI Service |
| Language | Python 3.11, SQL |

## Documentation

- [`CLAUDE.md`](CLAUDE.md) — project conventions and rules
- [`CLAUDE-PROGRESS.txt`](CLAUDE-PROGRESS.txt) — phase-by-phase progress tracker
- [`docs/architecture.md`](docs/architecture.md) — design decisions and ADRs
- [`docs/data_dictionary.md`](docs/data_dictionary.md) — table/column reference
- [`docs/business_questions.md`](docs/business_questions.md) — business questions driving the design

## Project structure

```
adventureworks-analytics/
├── data/        ← source CSV files (read-only)
├── database/    ← PostgreSQL DDL (staging + mart schemas)
├── loader/      ← Python loaders (full + incremental)
├── utils/       ← shared db connection, logging, file helpers
├── dbt/         ← staging models, mart models, snapshots, seeds, tests
├── airflow/     ← Docker Compose + DAG for orchestration
├── powerbi/     ← DAX measures and RLS setup notes
└── docs/        ← architecture, data dictionary, business questions
```

## Status

See [`CLAUDE-PROGRESS.txt`](CLAUDE-PROGRESS.txt) for current phase and task tracking.
