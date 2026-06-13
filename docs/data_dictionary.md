# Data Dictionary — AdventureWorks Analytics

**Version:** 1.0  
**Last updated:** 2026  
**Author:** Phil Dinh  
**Database:** PostgreSQL 15  
**Schemas:** `staging`, `mart`

---

## Overview

This dictionary covers all tables in the `mart` schema — the star schema layer that
Power BI connects to. Staging tables mirror these structures with two additional
metadata columns (`loaded_at`, `batch_id`) and no surrogate keys or SCD columns.

**Naming conventions:**
- `_sk` suffix = surrogate key (warehouse-generated, never from source)
- `_key` suffix = natural key (from source system / D365)
- `scd_` prefix = slowly changing dimension tracking column
- `loaded_at` = timestamp this row was loaded into staging
- `batch_id` = identifier for the pipeline run that loaded this row

---

## Fact Tables

---

### `mart.fact_sales`

**Description:** One row per order line item. The primary transactional fact table
capturing all sales across all territories from 2020 to 2026.  
**Grain:** One row per (OrderNumber + OrderLineItem + OrderDate)  
**Load strategy:** Incremental — append new rows where `loaded_at > last watermark`  
**Surrogate key:** `md5(OrderNumber || OrderLineItem || OrderDate)`

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `order_sk` | CHAR(32) | NOT NULL | Surrogate PK — md5 hash of OrderNumber + OrderLineItem + OrderDate |
| `OrderDate` | DATE | NOT NULL | Date the order was placed |
| `StockDate` | DATE | NOT NULL | Date stock was allocated for this order |
| `OrderNumber` | VARCHAR(20) | NOT NULL | Natural order identifier from source (e.g. SO48797) |
| `ProductKey` | INT | NOT NULL | FK → `mart.dim_product.ProductKey` |
| `CustomerKey` | INT | NOT NULL | FK → `mart.dim_customer.CustomerKey` |
| `TerritoryKey` | INT | NOT NULL | FK → `mart.dim_territory.SalesTerritoryKey` |
| `OrderLineItem` | SMALLINT | NOT NULL | Line number within the order (1–8) |
| `OrderQuantity` | SMALLINT | NOT NULL | Units ordered (1–4) |
| `loaded_at` | TIMESTAMP | NOT NULL | When this row was loaded into staging |
| `batch_id` | VARCHAR(50) | NOT NULL | Pipeline run identifier (YYYYMMDD_HHmmss) |

**Notes:**
- Revenue and profit are not stored — calculated in DAX as `OrderQuantity × ProductPrice` and `OrderQuantity × (ProductPrice − ProductCost)` using `dim_product` values
- ProductPrice and ProductCost join from `dim_product` — SCD2 ensures the historically correct price is used for each order date
- `OrderDate` is part of the surrogate key because the source data reuses 242 `(OrderNumber, OrderLineItem)` pairs across different `OrderDate` values — see ADR-010 in `docs/architecture.md`

---

### `mart.fact_returns`

**Description:** One row per return event per product per territory per date.
Captures all product returns across all territories from 2020 to 2026.  
**Grain:** One row per (ReturnDate + TerritoryKey + ProductKey)  
**Load strategy:** Incremental — append new rows where `loaded_at > last watermark`  
**Surrogate key:** `md5(ReturnDate || TerritoryKey || ProductKey)`

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `return_sk` | CHAR(32) | NOT NULL | Surrogate PK — md5 hash of ReturnDate + TerritoryKey + ProductKey |
| `ReturnDate` | DATE | NOT NULL | Date the return was processed |
| `TerritoryKey` | INT | NOT NULL | FK → `mart.dim_territory.SalesTerritoryKey` |
| `ProductKey` | INT | NOT NULL | FK → `mart.dim_product.ProductKey` |
| `ReturnQuantity` | SMALLINT | NOT NULL | Units returned (1–2) |
| `loaded_at` | TIMESTAMP | NOT NULL | When this row was loaded into staging |
| `batch_id` | VARCHAR(50) | NOT NULL | Pipeline run identifier (YYYYMMDD_HHmmss) |

**Notes:**
- No CustomerKey — returns are not linked to specific customers in the source data
- Return Rate = `fact_returns[ReturnQuantity]` / `fact_sales[Total Orders]` — requires both facts in the Power BI model
- Rows sharing a `(ReturnDate, TerritoryKey, ProductKey)` combination in the source data are aggregated (`ReturnQuantity` summed) to match this grain — see ADR-011 in `docs/architecture.md`

---

## Dimension Tables

---

### `mart.dim_customer`

**Description:** One current row per customer. Historical versions tracked via SCD Type 2
on income, marital status, home ownership, and occupation.  
**SCD Strategy:** Type 2 on `AnnualIncome`, `MaritalStatus`, `HomeOwner`, `Occupation` — Type 1 on all other attributes  
**Managed by:** `dbt snapshot` (snap_customer)

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `customer_sk` | INT IDENTITY | NOT NULL | Surrogate PK — warehouse generated |
| `CustomerKey` | INT | NOT NULL | Natural key from source (1–18,148) |
| `Prefix` | VARCHAR(5) | NULL | Title (MR. / MRS. / MS.) — SCD Type 1 |
| `FirstName` | VARCHAR(50) | NOT NULL | Customer first name — SCD Type 1 |
| `LastName` | VARCHAR(50) | NOT NULL | Customer last name — SCD Type 1 |
| `BirthDate` | DATE | NOT NULL | Date of birth |
| `MaritalStatus` | CHAR(1) | NOT NULL | M = Married, S = Single — **SCD Type 2** |
| `Gender` | CHAR(1) | NULL | M = Male, F = Female — SCD Type 1 |
| `EmailAddress` | VARCHAR(100) | NOT NULL | Unique email — SCD Type 1 |
| `AnnualIncome` | INT | NOT NULL | Annual income in USD — **SCD Type 2** |
| `TotalChildren` | SMALLINT | NOT NULL | Number of children (0–5) |
| `EducationLevel` | VARCHAR(30) | NOT NULL | Partial High School / High School / Partial College / Bachelors / Graduate Degree — SCD Type 1 |
| `Occupation` | VARCHAR(30) | NOT NULL | Clerical / Manual / Skilled Manual / Professional / Management — **SCD Type 2** |
| `HomeOwner` | CHAR(1) | NOT NULL | Y = Owns home, N = Does not — **SCD Type 2** |
| `scd_start_date` | DATE | NOT NULL | Date this version became active |
| `scd_end_date` | DATE | NULL | Date this version was superseded (NULL = current) |
| `scd_is_current` | BOOLEAN | NOT NULL | TRUE = current active record |
| `scd_version` | SMALLINT | NOT NULL | Version number (starts at 1) |

**Notes:**
- Power BI connects with `WHERE scd_is_current = TRUE` to get one row per customer
- Income Level bucketing (Low / Average / High) is a DAX calculated column in Power BI, not stored here
- Full Name is concatenated in Power BI: `Prefix & " " & FirstName & " " & LastName`

---

### `mart.dim_product`

**Description:** One current row per product. Historical versions tracked via SCD Type 2
on cost and price — critical for accurate historical margin calculations.  
**SCD Strategy:** Type 2 on `ProductCost`, `ProductPrice` — Type 1 on all other attributes  
**Managed by:** `dbt snapshot` (snap_product)

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `product_sk` | INT IDENTITY | NOT NULL | Surrogate PK — warehouse generated |
| `ProductKey` | INT | NOT NULL | Natural key from source (1–293) |
| `ProductSubcategoryKey` | INT | NOT NULL | FK → `mart.dim_product_subcategory.ProductSubcategoryKey` |
| `ProductSKU` | VARCHAR(20) | NOT NULL | Stock keeping unit code (e.g. HL-U509-R) |
| `ProductName` | VARCHAR(100) | NOT NULL | Full product name — SCD Type 1 |
| `ModelName` | VARCHAR(100) | NOT NULL | Product model family name — SCD Type 1 |
| `ProductDescription` | VARCHAR(500) | NOT NULL | Marketing description — SCD Type 1 |
| `ProductColor` | VARCHAR(20) | NULL | Colour name — NULL for non-coloured items, stored as 'N/A' — SCD Type 1 |
| `ProductSize` | VARCHAR(5) | NOT NULL | Size code (XS/S/M/L/XL) or '0' for non-sized items — SCD Type 1 |
| `ProductStyle` | VARCHAR(5) | NOT NULL | Style code (U/M/W) or '0' for non-styled items — SCD Type 1 |
| `ProductCost` | NUMERIC(10,4) | NOT NULL | Unit cost in USD — **SCD Type 2** |
| `ProductPrice` | NUMERIC(10,2) | NOT NULL | Unit selling price in USD — **SCD Type 2** |
| `scd_start_date` | DATE | NOT NULL | Date this version became active |
| `scd_end_date` | DATE | NULL | Date this version was superseded (NULL = current) |
| `scd_is_current` | BOOLEAN | NOT NULL | TRUE = current active record |
| `scd_version` | SMALLINT | NOT NULL | Version number (starts at 1) |

**Notes:**
- Revenue = `fact_sales[OrderQuantity]` × `dim_product[ProductPrice]`
- Profit = `fact_sales[OrderQuantity]` × (`dim_product[ProductPrice]` − `dim_product[ProductCost]`)
- Power BI joins on `ProductKey` with date bridging to get the historically correct price version

---

### `mart.dim_territory`

**Description:** One row per sales territory. Static — no SCD tracking required.  
**Load strategy:** Full load (15 rows, never changes)

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `territory_sk` | INT IDENTITY | NOT NULL | Surrogate PK — warehouse generated |
| `SalesTerritoryKey` | INT | NOT NULL | Natural key from source (1–15) |
| `Region` | VARCHAR(50) | NOT NULL | Region name (e.g. Northwest, New South Wales) |
| `Country` | VARCHAR(50) | NOT NULL | Country name |
| `Continent` | VARCHAR(20) | NOT NULL | North America / Europe / Pacific |
| `Latitude` | NUMERIC(8,4) | NOT NULL | Geographic centroid latitude — used for Bing map |
| `Longitude` | NUMERIC(8,4) | NOT NULL | Geographic centroid longitude — used for Bing map |

**Territory Reference:**

| Key | Region | Country | Continent |
|---|---|---|---|
| 1–5 | Northwest, Northeast, Central, Southwest, Southeast | United States | North America |
| 6 | Canada | Canada | North America |
| 7–10 | France, Germany, Poland, United Kingdom | Europe | Europe |
| 11–13 | New South Wales, Victoria, Queensland | Australia | Pacific |
| 14–15 | North Island, South Island | New Zealand | Pacific |

**Notes:**
- RLS roles in Power BI Service are defined on `Continent` and `Country`
- AU/NZ territories (11–15) were added to extend the dataset for Pacific market relevance

---

### `mart.dim_calendar`

**Description:** One row per date from 2020-01-01 to 2026-12-31.
Fully generated in dbt — not loaded from CSV.  
**Load strategy:** Generated via dbt macro in `models/utils/dim_calendar.sql`

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `Date` | DATE | NOT NULL | PK — calendar date |
| `DateKey` | INT | NOT NULL | Integer date key (YYYYMMDD) for fast joins |
| `Year` | SMALLINT | NOT NULL | Calendar year (2020–2026) |
| `QuarterNumber` | SMALLINT | NOT NULL | Quarter number (1–4) |
| `QuarterName` | VARCHAR(6) | NOT NULL | Quarter label (Q1–Q4) |
| `MonthNumber` | SMALLINT | NOT NULL | Month number (1–12) |
| `MonthName` | VARCHAR(10) | NOT NULL | Full month name (January–December) |
| `MonthShort` | VARCHAR(3) | NOT NULL | Abbreviated month (Jan–Dec) |
| `WeekNumber` | SMALLINT | NOT NULL | ISO week number (1–53) |
| `DayOfWeek` | SMALLINT | NOT NULL | Day number (1=Monday, 7=Sunday) |
| `DayName` | VARCHAR(10) | NOT NULL | Full day name (Monday–Sunday) |
| `DayShort` | VARCHAR(3) | NOT NULL | Abbreviated day (Mon–Sun) |
| `IsWeekend` | BOOLEAN | NOT NULL | TRUE for Saturday and Sunday |
| `IsWeekday` | BOOLEAN | NOT NULL | TRUE for Monday–Friday |
| `MonthYear` | VARCHAR(8) | NOT NULL | Display label (e.g. Jan 2024) |
| `YearMonth` | INT | NOT NULL | Sortable year-month integer (YYYYMM) |

**Notes:**
- Power BI time intelligence (DATEADD, DATESYTD, SAMEPERIODLASTYEAR) requires this table to be marked as a Date Table on the `Date` column
- `YearMonth` is used for sorting MonthYear correctly in visuals (avoids alphabetical sort)

---

### `mart.dim_product_subcategory`

**Description:** Product subcategory reference. 37 rows. Loaded via `dbt seed`.  
**Load strategy:** `dbt seed` — static reference data

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `ProductSubcategoryKey` | INT | NOT NULL | PK — natural key (1–37) |
| `SubcategoryName` | VARCHAR(50) | NOT NULL | Subcategory name (e.g. Mountain Bikes, Tires and Tubes) |
| `ProductCategoryKey` | INT | NOT NULL | FK → `mart.dim_product_category.ProductCategoryKey` |

---

### `mart.dim_product_category`

**Description:** Top-level product category reference. 4 rows. Loaded via `dbt seed`.  
**Load strategy:** `dbt seed` — static reference data

| Column | Data Type | Nullable | Description |
|---|---|---|---|
| `ProductCategoryKey` | INT | NOT NULL | PK — natural key (1–4) |
| `CategoryName` | VARCHAR(20) | NOT NULL | Category name |

**Category Reference:**

| Key | Category |
|---|---|
| 1 | Bikes |
| 2 | Components |
| 3 | Clothing |
| 4 | Accessories |

---

## Staging Tables

Staging tables live in the `staging` schema and mirror the mart structure with two differences:

1. No surrogate keys — natural keys only
2. Two additional metadata columns on every table:

| Column | Data Type | Description |
|---|---|---|
| `loaded_at` | TIMESTAMP | When this row was inserted into staging by the Python loader |
| `batch_id` | VARCHAR(50) | Pipeline run identifier — format YYYYMMDD_HHmmss |

Staging tables are the dbt source (`{{ source('staging', 'table_name') }}`).
They are never queried by Power BI directly.

---

## Source to Mart Column Mapping

### fact_sales

| Source CSV Column | Staging Column | Mart Column | Transformation |
|---|---|---|---|
| `OrderDate` | `OrderDate` | `OrderDate` | Cast to DATE, dayfirst=True |
| `StockDate` | `StockDate` | `StockDate` | Cast to DATE, dayfirst=True |
| `OrderNumber` | `OrderNumber` | `OrderNumber` | None |
| `ProductKey` | `ProductKey` | `ProductKey` | None |
| `CustomerKey` | `CustomerKey` | `CustomerKey` | None |
| `TerritoryKey` | `TerritoryKey` | `TerritoryKey` | None |
| `OrderLineItem` | `OrderLineItem` | `OrderLineItem` | Cast to SMALLINT |
| `OrderQuantity` | `OrderQuantity` | `OrderQuantity` | Cast to SMALLINT |
| — | `loaded_at` | `loaded_at` | Added by Python loader |
| — | `batch_id` | `batch_id` | Added by Python loader |
| — | — | `order_sk` | Generated in dbt: md5(OrderNumber \|\| OrderLineItem) |

### dim_customer

| Source CSV Column | Staging Column | Mart Column | Transformation |
|---|---|---|---|
| `CustomerKey` | `CustomerKey` | `CustomerKey` | None |
| `Prefix` | `Prefix` | `Prefix` | TRIM, NULLIF('', NULL) |
| `FirstName` | `FirstName` | `FirstName` | INITCAP |
| `LastName` | `LastName` | `LastName` | INITCAP |
| `BirthDate` | `BirthDate` | `BirthDate` | Cast to DATE, dayfirst=True |
| `MaritalStatus` | `MaritalStatus` | `MaritalStatus` | None |
| `Gender` | `Gender` | `Gender` | NULLIF('', NULL) |
| `EmailAddress` | `EmailAddress` | `EmailAddress` | LOWER, TRIM |
| `AnnualIncome` | `AnnualIncome` | `AnnualIncome` | Cast to INT |
| `TotalChildren` | `TotalChildren` | `TotalChildren` | Cast to SMALLINT |
| `EducationLevel` | `EducationLevel` | `EducationLevel` | None |
| `Occupation` | `Occupation` | `Occupation` | None |
| `HomeOwner` | `HomeOwner` | `HomeOwner` | None |
| — | — | `customer_sk` | Generated by dbt snapshot |
| — | — | `scd_*` columns | Generated by dbt snapshot |

### dim_product

| Source CSV Column | Staging Column | Mart Column | Transformation |
|---|---|---|---|
| `ProductKey` | `ProductKey` | `ProductKey` | None |
| `ProductSubcategoryKey` | `ProductSubcategoryKey` | `ProductSubcategoryKey` | None |
| `ProductSKU` | `ProductSKU` | `ProductSKU` | None |
| `ProductName` | `ProductName` | `ProductName` | None |
| `ModelName` | `ModelName` | `ModelName` | None |
| `ProductDescription` | `ProductDescription` | `ProductDescription` | NULLIF('0', NULL) |
| `ProductColor` | `ProductColor` | `ProductColor` | COALESCE(NULL, 'N/A') |
| `ProductSize` | `ProductSize` | `ProductSize` | NULLIF('0', 'N/A') |
| `ProductStyle` | `ProductStyle` | `ProductStyle` | NULLIF('0', 'N/A') |
| `ProductCost` | `ProductCost` | `ProductCost` | Cast to NUMERIC(10,4) |
| `ProductPrice` | `ProductPrice` | `ProductPrice` | Cast to NUMERIC(10,2) |
| — | — | `product_sk` | Generated by dbt snapshot |
| — | — | `scd_*` columns | Generated by dbt snapshot |
