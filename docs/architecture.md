# Architecture — AdventureWorks Analytics

**Version:** 1.0  
**Last updated:** 2026  
**Author:** Phil Dinh

---

## 1. Project Purpose

This project builds a production-grade analytics solution for AdventureWorks Bike Shop —
a retail and supply chain dataset treated as a Microsoft Dynamics 365 export.

The goal is to answer C-suite business questions about revenue, profitability, product
performance, regional distribution, and customer behaviour across 2020–2026.

The three core outputs are:
- A clean, tested star schema data warehouse in PostgreSQL
- A fully orchestrated ELT pipeline (Python → dbt → Airflow)
- A multi-page Power BI report with DAX measures and Row Level Security

---

## 2. Business Questions Driving the Design

**Level 1 — Executive**
- Is the business growing and are we profitable?
- Where are we losing money through returns?

**Level 2 — Operational**
- How is revenue and profit trending month over month and year over year?
- Which product categories and regions drive the most orders?
- Are we hitting monthly targets?

**Level 3 — Analytical**
- Which products have unacceptable return rates?
- Who are our highest-value customers and what is their demographic profile?
- How does profit change if we adjust product pricing?
- Which territory (including AU/NZ) is growing fastest?

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SOURCE LAYER                             │
│   CSV files (D365 export simulation) — /data/                   │
│   fact_sales · fact_returns · dim_customer · dim_product        │
│   dim_territory · dim_calendar                                  │
└────────────────────────┬────────────────────────────────────────┘
                         │ Python loader (load_full / load_incremental)
                         │ adds loaded_at + batch_id
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      STAGING SCHEMA                             │
│   PostgreSQL — schema: staging                                  │
│   Raw data as-is + metadata columns                             │
│   Views only — no transformations                               │
└────────────────────────┬────────────────────────────────────────┘
                         │ dbt run (stg_ models → mart_ models)
                         │ dbt snapshot (SCD Type 2)
                         │ dbt seed (static dims)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                       MART SCHEMA                               │
│   PostgreSQL — schema: mart                                     │
│   Star schema: 2 facts + 6 dims                                 │
│   Surrogate keys · SCD2 history · Tested                        │
└────────────────────────┬────────────────────────────────────────┘
                         │ Power BI Import mode
                         │ Nightly refresh
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│   Power BI Desktop → Power BI Service                           │
│   4 dashboard pages · DAX measures · RLS                        │
└─────────────────────────────────────────────────────────────────┘

  All layers orchestrated by Apache Airflow running in Docker
```

---

## 4. Data Warehouse Design

### Schema Strategy: Two Layers Only

Staging and mart. No medallion architecture (bronze/silver/gold).

**Why:** Source data is treated as a D365 export — structured, typed, and clean at the
point of extraction. A medallion architecture solves the problem of raw, unstructured, or
multi-source data landing in a data lake. That problem does not exist here. Adding a
bronze layer would introduce unnecessary complexity without any quality benefit.

### Star Schema — Mart Layer

```
                    dim_calendar
                         │
dim_customer ────── fact_sales ────── dim_territory
                         │
                    dim_product
                         │
              dim_product_subcategory
                         │
               dim_product_category

                    dim_calendar
                         │
dim_product ────── fact_returns ───── dim_territory
```

**Conformed dimensions:** `dim_product`, `dim_territory`, and `dim_calendar` are shared
across both facts. This enables cross-fact analysis (e.g. return rate = returns / sales)
in a single Power BI model without role-playing or duplicating dimensions.

### Fact Table Grains

| Fact | Grain | Rows (approx) |
|---|---|---|
| `fact_sales` | One row per order line item | ~341,000 |
| `fact_returns` | One row per (ReturnDate + TerritoryKey + ProductKey) | ~4,500 |

### Slowly Changing Dimensions

| Dimension | Strategy | Tracked Attributes |
|---|---|---|
| `dim_customer` | SCD Type 2 | AnnualIncome, MaritalStatus, HomeOwner, Occupation |
| `dim_customer` | SCD Type 1 | Prefix, EmailAddress, Gender, EducationLevel |
| `dim_product` | SCD Type 2 | ProductCost, ProductPrice |
| `dim_product` | SCD Type 1 | ProductName, ProductDescription, ProductColor, ProductSize, ProductStyle |
| `dim_territory` | Static | — |
| `dim_product_category` | Static (seed) | — |
| `dim_product_subcategory` | Static (seed) | — |
| `dim_calendar` | Generated | — |

**Why SCD Type 2 on ProductCost and ProductPrice:** Price and cost changes are business
events. Historical margin calculations would be wrong if we overwrote prices — a sale
made in 2021 at the old price should report the 2021 profit, not the 2024 profit.

**Why SCD Type 1 on ProductName:** Product name changes are corrections, not events.
Reporting a product under two names because of a typo fix would create confusion.

---

## 5. Surrogate Key Strategy

| Table Type | Key Type | Generation Method |
|---|---|---|
| Fact tables | `CHAR(32)` | `md5(natural key columns concatenated)` |
| Dimension tables | `INT` | `row_number()` generated in the dbt mart model (see ADR-009) |

**Why md5 for facts:** Deterministic — the same source row always produces the same
surrogate key. This makes incremental loads idempotent. Re-running a failed batch
produces no duplicates because the key already exists in the mart.

**Why row_number() for dims:** Dims are rebuilt by `dbt run` from `dbt snapshot` output,
which controls insert order. Sequential integers are readable and join-efficient in
VertiPaq. `CREATE TABLE AS SELECT` does not preserve `GENERATED ALWAYS AS IDENTITY`
(see ADR-009), so `row_number()` is the deterministic equivalent for a table that is
fully rebuilt on every run.

---

## 6. Incremental Load Strategy

**Pattern:** Timestamp watermark + hash surrogate deduplication

```
1. Python loader runs, adds loaded_at = datetime.now() and batch_id to every row
2. Rows land in staging schema
3. dbt incremental model runs:
   WHERE loaded_at > (SELECT MAX(loaded_at) FROM mart.fact_sales)
4. For each new row: if surrogate key exists → skip, if new → insert
5. Pipeline fails? Re-run. Same rows arrive, same md5 keys → no duplicates
```

**Why not CDC (Debezium/Kafka):** Source is CSV files. CDC requires a live database with
WAL/binlog enabled. Timestamp-based incremental is the correct pattern for batch
file exports and is used in production D365 integrations globally.

**Full load vs incremental:**
- `load_full.py` — run once to establish the baseline
- `load_incremental.py` — run nightly by Airflow, picks up only new rows

---

## 7. Static Dimensions — dbt Seeds

`dim_product_category` (4 rows) and `dim_product_subcategory` (37 rows) are loaded via
`dbt seed` rather than through the Python loader and staging schema.

**Why:** These tables never change. Running them through the full ELT pipeline
(loader → staging → dbt model) adds orchestration overhead for data that is static.
`dbt seed` loads them directly into the mart in one command and makes the data visible
in the dbt DAG as a dependency.

---

## 8. Orchestration

**Tool:** Apache Airflow running in Docker Compose alongside PostgreSQL.
The `postgres` service in `airflow/docker-compose.yml` is Airflow's own
metadata database — the `adventureworks` warehouse remains on the host
Postgres instance, reached via `host.docker.internal` (see ADR-012).

**DAG:** `adventureworks_pipeline`

```
load_csvs_to_staging → dbt_seed → dbt_snapshot → dbt_run → dbt_test
```

**Schedule:** Nightly (`@daily`)  
**Catchup:** False — missed runs are not backfilled  
**On failure:** Airflow retries once, then alerts. Because loads are idempotent,
safe to re-run without manual cleanup.

---

## 9. Power BI Architecture

**Connection mode:** Import

**Why Import over DirectQuery:** Dataset is small enough for VertiPaq compression.
Import loads all data into RAM as a columnar store — DAX executes entirely in-memory,
subsecond query response for all visuals. DirectQuery would round-trip to PostgreSQL
on every visual interaction — unnecessary latency with no benefit at this data volume.

**Model structure:**
- Two fact tables: `fact_sales` and `fact_returns`
- Six dimensions: all conformed, connected via their surrogate keys
- Relationship cardinality: all many-to-one (fact → dim)
- Filter direction: single — dim filters fact, never the reverse
- All DAX measures live in a dedicated `_Measures` table

**Row Level Security:**
- Defined on `dim_territory[Continent]` and `dim_territory[Country]`
- Role: `Pacific` — sees Australia and New Zealand only
- Role: `Europe` — sees UK, France, Germany, Poland only
- Role: `North America` — sees US and Canada only
- Applied in Power BI Service after publish

---

## 10. Architecture Decisions Log

### ADR-001: Two schemas instead of medallion
- **Decision:** staging + mart only
- **Reason:** Source is clean D365-structured CSV. Medallion solves raw/unstructured data problems that don't exist here.
- **Trade-off:** Less flexible if a truly raw source is added later. Acceptable for this scope.

### ADR-002: PostgreSQL over cloud warehouse
- **Decision:** Local PostgreSQL in Docker
- **Reason:** Portfolio project — demonstrates DWH design and dbt skills without cloud cost. Same DDL and dbt models are portable to Redshift/BigQuery/Snowflake.
- **Trade-off:** No cloud scalability. Not a concern at this data volume.

### ADR-003: Import mode over DirectQuery in Power BI
- **Decision:** Import mode
- **Reason:** Small dataset, nightly batch refresh cadence, VertiPaq performance advantages for DAX.
- **Trade-off:** Data is not real-time. Acceptable — business questions are trend-based, not operational.

### ADR-004: dbt snapshot for SCD Type 2
- **Decision:** Use `dbt snapshot` for customer and product dims
- **Reason:** Industry standard, built-in `check` strategy handles attribute comparison, produces clean SCD2 columns automatically.
- **Trade-off:** Snapshots run separately from `dbt run` — requires correct DAG ordering in Airflow.

### ADR-005: Timestamp watermark over CDC
- **Decision:** `loaded_at` column as incremental watermark
- **Reason:** Source is CSV files — no live database, no WAL/binlog to tap. Timestamp is the correct and common pattern for batch file exports.
- **Trade-off:** Does not capture deletes. Acceptable — source CSVs are append-only exports.

### ADR-006: No notebooks folder
- **Decision:** Excluded `notebooks/`
- **Reason:** Dataset is a structured D365 export. Schema and data quality are known upfront. EDA notebooks are for unknown datasets.
- **Trade-off:** None — adds no value here.

### ADR-007: No staging.dim_calendar table
- **Decision:** `01_create_staging_schema.sql` defines 5 staging tables (fact_sales, fact_returns, dim_customer, dim_product, dim_territory) — no `staging.dim_calendar`.
- **Reason:** `dim_calendar` is fully generated by `models/utils/dim_calendar.sql` (2020-01-01 to 2026-12-31), per the data dictionary. The source `AdventureWorks Calendar Lookup.csv` only covers ~2020-2022 and has a single `Date` column — incomplete and unnecessary given the dbt-generated table covers the full range with all required attributes.
- **Trade-off:** None — the high-level diagram in this doc listing `dim_calendar` as a CSV source is superseded by this decision.

### ADR-008: No FK constraints from fact tables to SCD2 dims
- **Decision:** `03_constraints_indexes.sql` does not add FK constraints from `fact_sales`/`fact_returns` to `dim_customer.CustomerKey` or `dim_product.ProductKey`.
- **Reason:** `dim_customer` and `dim_product` are SCD Type 2 — `CustomerKey`/`ProductKey` are not unique across historical versions, so they cannot be FK targets. Enforceable FKs were added instead for relationships with genuinely unique natural keys: `dim_product_subcategory → dim_product_category`, `dim_product → dim_product_subcategory`, `fact_* .TerritoryKey → dim_territory`, `fact_*.OrderDate/ReturnDate → dim_calendar`.
- **Trade-off:** Referential integrity for `fact_* → dim_customer/dim_product` is validated via dbt `relationships` schema tests (filtered to `scd_is_current = TRUE`) in Phase 3, not by the database.

### ADR-009: dbt fully owns the mart schema — remaining Phase 1 constraints dropped
- **Decision:** During Phase 3, the remaining PK/FK constraints from `03_constraints_indexes.sql` that target dbt-managed mart tables were dropped from the live database: `fk_subcategory_category` (`dim_product_subcategory` → `dim_product_category`), `fk_product_subcategory` (`dim_product` → `dim_product_subcategory`), `fk_sales_territory`, `fk_sales_calendar`, `fk_returns_territory`, `fk_returns_calendar`. Integer surrogate keys (`territory_sk`, `customer_sk`, `product_sk`) are generated with `row_number()` in the model SQL rather than relying on the `INT GENERATED ALWAYS AS IDENTITY` columns from `02_create_mart_schema.sql`.
- **Reason:**
  - `dbt seed` truncates and reloads seed tables on every run. `dim_product_subcategory` had an FK to `dim_product_category`, which Postgres refuses to truncate without `CASCADE` — `dbt seed` failed immediately.
  - `dbt run` table materialization rebuilds a table via create-temp → rename-old-to-backup → create-new → drop-backup. The drop-backup step fails if another table holds an FK pointing at it. `fact_sales`/`fact_returns` had FKs to `dim_territory` and `dim_calendar`, both table-materialized — every rebuild after the first would fail.
  - `CREATE TABLE AS SELECT` does not carry over `GENERATED ALWAYS AS IDENTITY`, so Phase 1's identity columns on `dim_territory`/`dim_customer`/`dim_product` would have been silently lost on the first `dbt run` regardless.
- **Trade-off:** No database-level referential integrity for these six relationships. All are validated via dbt tests instead: `relationships` schema tests for `fact_* .TerritoryKey → dim_territory.SalesTerritoryKey` and `fact_*.OrderDate/ReturnDate → dim_calendar.Date`, plus the custom `assert_sales_keys_valid` test for `fact_sales.CustomerKey/ProductKey → dim_customer/dim_product` (filtered to `scd_is_current`). This extends ADR-008's reasoning — dbt-managed mart tables are validated by dbt tests, not Postgres constraints — to the whole mart schema. `database/03_constraints_indexes.sql` remains as a record of the originally intended design but is no longer runnable as-is against a dbt-managed mart.

### ADR-010: fact_sales surrogate key includes OrderDate
- **Decision:** `order_sk = md5(OrderNumber || OrderLineItem || OrderDate)`, not `md5(OrderNumber || OrderLineItem)` as originally specified in the data dictionary.
- **Reason:** The source data (extended to span 2020–2026) contains 242 `(OrderNumber, OrderLineItem)` pairs that recur with different `OrderDate`/`ProductKey`/`CustomerKey` values — `OrderNumber` is reused across the extended date range. Adding `OrderDate` to the key produces zero collisions across all 341,168 rows.
- **Trade-off:** None observed — `OrderDate` is immutable per row, so the key stays deterministic and idempotent for incremental loads.

### ADR-011: fact_returns aggregates to its documented grain
- **Decision:** `fact_returns` groups staging rows by `(ReturnDate, TerritoryKey, ProductKey)` and sums `ReturnQuantity`, rather than passing rows through 1:1.
- **Reason:** One combination in the source data (`2024-01-24`, territory 3, product 185) appears as two separate rows with `ReturnQuantity = 1` each, violating the documented one-row-per-grain rule. Aggregating rolls these up to a single row with `ReturnQuantity = 2`, matching the documented grain.
- **Trade-off:** If a future incremental batch reports returns for a `(ReturnDate, TerritoryKey, ProductKey)` combination already present from an earlier batch, the new row reflects only the new batch's quantity (delete+insert replaces rather than adds). Acceptable here — return events are not expected to span batches at this grain.

### ADR-012: PostgreSQL for the warehouse stays on the Windows host — not containerized
- **Decision:** `airflow/docker-compose.yml` runs Airflow (webserver, scheduler, init) plus a `postgres` service — but that `postgres` service is Airflow's own metadata database only. The `adventureworks` warehouse database continues to run as the local Windows Postgres 16 service established in Phase 1 (see the Phase 1 note in `CLAUDE-PROGRESS.txt`). The Airflow containers reach it via `host.docker.internal`, with `DB_HOST` overridden to that value in the compose environment (all other `DB_*` vars are loaded from the project `.env` via `env_file`).
- **Reason:** The warehouse is already built, loaded (341k+ rows), and fully tested (Phase 3, 28/28 dbt tests) against the Windows Postgres instance. Containerizing it for Phase 4 would mean standing up a second Postgres, re-running `database/01-03` DDL and the full load + dbt pipeline, and repointing `.env` — pure migration work with no benefit to the orchestration goal of this phase.
- **Trade-off:** The stack is not fully portable via `docker-compose up` alone — a Postgres server must already exist on the host with the `adventureworks` database loaded. This is acceptable for a local portfolio project; `docs/architecture.md`'s "PostgreSQL in Docker" framing is superseded for the warehouse DB by this ADR (Airflow's own metadata DB is still containerized as designed).
