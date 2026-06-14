# AdventureWorks Analytics: End-to-End Retail BI Platform

I built a complete analytics platform for a retail business: raw sales, returns, customer
and product data flows through a PostgreSQL warehouse, gets transformed and tested with dbt,
refreshes automatically every night with Airflow in Docker, and lands in a 4-page Power BI
report that executives actually use to make decisions. 144K orders across 341K+ order lines,
18K customers, 2020 to 2026.

## 30-Second Summary

- **Who it's for:** Retail executives and regional leaders who need revenue, profit, and return
  rate at a glance, plus the ability to drill into any product, region, or customer
- **What it delivers:** A 4-page Power BI report tracking $606M in revenue, $255M in profit,
  144K orders, and a 0.5% return rate, with a regional map, product drill-through, and a
  top-100 customer view
- **How it stays current:** A fully automated nightly pipeline (Python, dbt, Airflow, Docker)
  that's idempotent, tested (28/28 dbt tests passing), and tracks historical changes to
  customers and products with SCD Type 2
- **Built like a real warehouse:** deliberate data types, constraints, and indexes for data
  quality and fast queries, plus incremental models so nightly refreshes only touch what changed
- **DAX done properly:** a real star-schema semantic model, measures built on filter context
  and row context (not calculated columns), and time intelligence for MoM trends
- **What it shows about me:** I can take a business problem from "what does leadership need to
  know" all the way through data modeling, warehouse design, ETL, orchestration, and a
  polished, performant dashboard

---

## 1. Starting With the Business Questions

Every good analytics project starts with who's asking and why. Here, the end users are
retail executives, and their questions drive everything downstream:

| Level | Questions |
|---|---|
| **Executive** | Is the business growing and profitable? Where are we losing money on returns? |
| **Operational** | How is revenue and profit trending month over month and year over year? Which categories and regions drive orders? |
| **Analytical** | Which products have high return rates? Who are our highest-value customers? How does profit respond to price changes? |

I started by mapping these questions against a simulated Dynamics 365 export to decide
exactly which entities were worth modeling, and which weren't:

![Entity map by source system](docs/images/entity-source.png)

Full list in [`docs/business_questions.md`](docs/business_questions.md).

---

## 2. Data Model: Star Schema

Those business questions became a 2-fact / 6-dim star schema: `fact_sales` and `fact_returns`
at the center, surrounded by `dim_customer`, `dim_product`, `dim_product_category` /
`dim_product_subcategory`, `dim_territory`, and `dim_calendar`.

![Entity relationship diagram](docs/images/entity-relationship.png)

---

## 3. Data Warehouse Design: Built for Quality, Performance, and Easy Refreshes

A star schema is only as good as the table design behind it. A few choices that matter:

- **Right-sized data types**: `NUMERIC(10,4)` / `NUMERIC(10,2)` for cost and price so financial
  math never drifts from floating-point rounding, `SMALLINT` for small bounded values (order
  line numbers, quantities, SCD versions), `CHAR(1)` for single-character flags (gender,
  marital status, homeowner), and a fixed `CHAR(32)` for md5 surrogate keys so every fact row
  joins on a constant-width key
- **Constraints that catch problems early**: every table has a primary key and `NOT NULL` on
  business-critical columns, with foreign keys linking the static dimensions (territory,
  product category/subcategory). SCD2 dimensions (customer, product) can't be FK targets since
  they carry multiple historical rows per natural key, so dbt `relationships` tests, filtered
  to the current row, do that job instead
- **Indexes built around how the data is queried**: every fact-to-dimension join column
  (`ProductKey`, `CustomerKey`, `TerritoryKey`, `OrderDate`/`ReturnDate`) is indexed, a partial
  index on `scd_is_current` makes "give me the current version" lookups instant, and a
  watermark index on `loaded_at` keeps incremental loads fast as staging grows
- **Incremental models for fast, light refreshes**: `fact_sales` and `fact_returns` are dbt
  incremental models using delete+insert on a deterministic md5 key, so a nightly refresh only
  touches new or changed rows instead of rebuilding 341K+ rows from scratch every night
- **28 automated data quality tests** run on every `dbt test`, generic checks (uniqueness,
  not-null, referential integrity) plus custom ones (no duplicate orders, every sales row maps
  to a valid current customer/product), catching bad data before it ever reaches Power BI

---

## 4. ETL Pipeline: Python to PostgreSQL

Python loaders (`load_full.py`, `load_incremental.py`, `load_dims.py`) read the source CSVs
and land them in a PostgreSQL `staging` schema. Loads are append-only, with `batch_id` and
`loaded_at` stamped once per run, and every load writes a row to `staging.etl_log` so there's
a full audit trail of what ran, when, and how many rows landed.

![ETL run log in staging.etl_log](docs/images/etl-log.png)

---

## 5. Transformation: dbt + SCD Type 2

dbt turns `staging` into `mart`: clean typed staging views, two seeded static dimensions, and
fully tested mart tables (28/28 dbt tests passing). `dim_customer` and `dim_product` are built
from `dbt snapshot`, giving full SCD Type 2 history on income, marital status, homeownership,
and occupation for customers, and on cost and price for products. Every row carries
`scd_start_date`, `scd_end_date`, `scd_is_current`, and `scd_version`, so a profit report from
2022 still reflects 2022 prices, not today's.

| Customer history | Product history |
|---|---|
| ![Customer SCD2 history](docs/images/customer-scd-screenshot.png) | ![Product SCD2 history](docs/images/product-scd-screenshot.png) |

---

## 6. Orchestration: Airflow in Docker

A single Airflow DAG, running in Docker Compose, drives the nightly refresh:
`load_facts_incremental` and `load_dims_full` run in parallel, then `dbt seed`, `dbt snapshot`,
`dbt run`, and `dbt test` run in sequence. The whole thing is idempotent: I've run it multiple
times end to end and `mart` never picks up a duplicate row.

![Airflow DAG run](docs/images/etl-dag.png)

---

## 7. The Dashboard: Power BI

Power BI connects to the `mart` schema only, in Import mode. The report has four pages, each
answering one tier of the business questions above, plus row-level security on
`dim_territory[Continent]` and `[Country]` so regional leaders only see their own market.

**Executive Summary**, *"Is the business healthy?"*
Revenue, profit, orders, and return rate at a glance, plus monthly trend and top 10 products.

![Executive Summary](docs/images/Executive-page.png)

**Regional Map**, *"Where is the business performing?"*
Revenue, profit, and orders by country and continent, filterable by region.

![Regional Map](docs/images/map-page.png)

**Product Drill-through**, *"How is this product doing, and what if we changed the price?"*
Monthly orders, revenue, and profit vs. target, with a live price-adjustment slider.

![Product drill-through](docs/images/product-page-drill-executive.png)

**Customer Detail**, *"Who are our customers, and which ones matter most?"*
Customer count and revenue-per-customer trend, segmented by income and occupation, with a
top-100 customer leaderboard.

![Customer Detail](docs/images/customer-page.png)

**Semantic model**: relationships between fact and dimension tables in Power BI

![Power BI data model](docs/images/data-model-powerbi.png)

---

## 8. DAX & the Power BI Data Model

The semantic model mirrors the warehouse: fact tables surrounded by dimension tables, all
single-direction filters from dimension to fact, with `dim_product`, `dim_territory`, and
`dim_calendar` shared (conformed) across both `fact_sales` and `fact_returns`. All measures
live in a separate `_Measures` table, no calculated columns.

- **Filter context**: every visual, slicer, and row-level security role applies a filter
  context that flows from dimensions down to facts through the model relationships. Put
  `Country` on the regional map, and every measure recalculates for just that country,
  automatically
- **Row context**: measures like Total Revenue aren't stored columns, they're calculated row
  by row with `SUMX`, multiplying each order line's quantity by the related product's price
  before summing:
  ```dax
  Total Revenue = SUMX(fact_sales, fact_sales[OrderQuantity] * RELATED(dim_product[ProductPrice]))
  Total Profit  = SUMX(fact_sales, fact_sales[OrderQuantity] * (RELATED(dim_product[ProductPrice]) - RELATED(dim_product[ProductCost])))
  Total Orders  = DISTINCTCOUNT(fact_sales[OrderNumber])
  Return Rate % = DIVIDE([Total Returns], [Total Orders])
  ```
- **Time intelligence**: month-over-month deltas use `dim_calendar` and `DATEADD` to shift the
  filter context back a period and compare:
  ```dax
  MoM Revenue Δ = [Total Revenue] - CALCULATE([Total Revenue], DATEADD(dim_calendar[Date], -1, MONTH))
  ```
- **What-if parameters**: the product drill-through page's price-adjustment slider feeds an
  Adjusted Profit measure that recalculates profit under a hypothetical price, in real time,
  for any product
- **Row-level security**: roles defined on `dim_territory[Continent]` / `[Country]` apply an
  extra filter context per user, so the exact same measures and visuals show different numbers
  depending on who's logged in

---

## Tech Stack

| Layer | Tool |
|---|---|
| Source | CSV files (simulated D365 export) |
| Database | PostgreSQL 16 |
| Transformation | dbt (staging views, mart tables, snapshots) |
| Orchestration | Apache Airflow + Docker Compose |
| Visualisation | Power BI Desktop, Power BI Service |
| Language | Python 3.11, SQL |

## Documentation

- [`docs/architecture.md`](docs/architecture.md): design decisions and ADRs
- [`docs/data_dictionary.md`](docs/data_dictionary.md): table/column reference
- [`docs/business_questions.md`](docs/business_questions.md): business questions driving the design
- [`CLAUDE-PROGRESS.txt`](CLAUDE-PROGRESS.txt): phase-by-phase progress tracker

## Project Structure

```
adventureworks-analytics/
├── data/        ← source CSV files (read-only)
├── database/    ← PostgreSQL DDL (staging + mart schemas)
├── loader/      ← Python loaders (full, incremental, dims)
├── utils/       ← shared db connection, logging, file helpers
├── dbt/         ← staging models, mart models, snapshots, seeds, tests
├── airflow/     ← Docker Compose + DAG for orchestration
├── powerbi/     ← Power BI report, DAX measures, RLS setup
└── docs/        ← architecture, data dictionary, business questions, images
```
