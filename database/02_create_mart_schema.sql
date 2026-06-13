-- ============================================================================
-- 02_create_mart_schema.sql
-- Mart schema — star schema tables that Power BI connects to.
-- Column definitions only (types, identity, not-null). Primary keys, foreign
-- keys, and indexes are added in 03_constraints_indexes.sql.
-- dbt owns the contents of these tables (seed / snapshot / run); this DDL
-- defines the agreed target structure documented in docs/data_dictionary.md.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS mart;

-- ----------------------------------------------------------------------------
-- mart.dim_product_category
-- Loaded via: dbt seed (dbt/seeds/dim_product_category.csv)
-- ----------------------------------------------------------------------------
CREATE TABLE mart.dim_product_category (
    "ProductCategoryKey" INT          NOT NULL,
    "CategoryName"       VARCHAR(20)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.dim_product_subcategory
-- Loaded via: dbt seed (dbt/seeds/dim_product_subcategory.csv)
-- ----------------------------------------------------------------------------
CREATE TABLE mart.dim_product_subcategory (
    "ProductSubcategoryKey" INT          NOT NULL,
    "SubcategoryName"       VARCHAR(50)  NOT NULL,
    "ProductCategoryKey"    INT          NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.dim_territory
-- Loaded via: dbt run (models/mart/dim_territory.sql), static, 15 rows
-- ----------------------------------------------------------------------------
CREATE TABLE mart.dim_territory (
    territory_sk        INT GENERATED ALWAYS AS IDENTITY,
    "SalesTerritoryKey" INT           NOT NULL,
    "Region"            VARCHAR(50)   NOT NULL,
    "Country"           VARCHAR(50)   NOT NULL,
    "Continent"         VARCHAR(20)   NOT NULL,
    "Latitude"          NUMERIC(8,4)  NOT NULL,
    "Longitude"         NUMERIC(8,4)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.dim_calendar
-- Generated via: dbt run (models/utils/dim_calendar.sql), 2020-01-01 to 2026-12-31
-- ----------------------------------------------------------------------------
CREATE TABLE mart.dim_calendar (
    "Date"        DATE         NOT NULL,
    "DateKey"     INT          NOT NULL,
    "Year"        SMALLINT     NOT NULL,
    "QuarterNumber" SMALLINT   NOT NULL,
    "QuarterName" VARCHAR(6)   NOT NULL,
    "MonthNumber" SMALLINT     NOT NULL,
    "MonthName"   VARCHAR(10)  NOT NULL,
    "MonthShort"  VARCHAR(3)   NOT NULL,
    "WeekNumber"  SMALLINT     NOT NULL,
    "DayOfWeek"   SMALLINT     NOT NULL,
    "DayName"     VARCHAR(10)  NOT NULL,
    "DayShort"    VARCHAR(3)   NOT NULL,
    "IsWeekend"   BOOLEAN      NOT NULL,
    "IsWeekday"   BOOLEAN      NOT NULL,
    "MonthYear"   VARCHAR(8)   NOT NULL,
    "YearMonth"   INT          NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.dim_customer
-- Loaded via: dbt run (models/mart/dim_customer.sql), reads snap_customer
-- SCD Type 2 on AnnualIncome, MaritalStatus, HomeOwner, Occupation
-- ----------------------------------------------------------------------------
CREATE TABLE mart.dim_customer (
    customer_sk      INT GENERATED ALWAYS AS IDENTITY,
    "CustomerKey"    INT           NOT NULL,
    "Prefix"         VARCHAR(5),
    "FirstName"      VARCHAR(50)   NOT NULL,
    "LastName"       VARCHAR(50)   NOT NULL,
    "BirthDate"      DATE          NOT NULL,
    "MaritalStatus"  CHAR(1)       NOT NULL,
    "Gender"         CHAR(1),
    "EmailAddress"   VARCHAR(100)  NOT NULL,
    "AnnualIncome"   INT           NOT NULL,
    "TotalChildren"  SMALLINT      NOT NULL,
    "EducationLevel" VARCHAR(30)   NOT NULL,
    "Occupation"     VARCHAR(30)   NOT NULL,
    "HomeOwner"      CHAR(1)       NOT NULL,
    scd_start_date   DATE          NOT NULL,
    scd_end_date     DATE,
    scd_is_current   BOOLEAN       NOT NULL,
    scd_version      SMALLINT      NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.dim_product
-- Loaded via: dbt run (models/mart/dim_product.sql), reads snap_product
-- SCD Type 2 on ProductCost, ProductPrice
-- ----------------------------------------------------------------------------
CREATE TABLE mart.dim_product (
    product_sk              INT GENERATED ALWAYS AS IDENTITY,
    "ProductKey"            INT            NOT NULL,
    "ProductSubcategoryKey" INT            NOT NULL,
    "ProductSKU"            VARCHAR(20)    NOT NULL,
    "ProductName"           VARCHAR(100)   NOT NULL,
    "ModelName"             VARCHAR(100)   NOT NULL,
    "ProductDescription"    VARCHAR(500)   NOT NULL,
    "ProductColor"          VARCHAR(20)    NOT NULL,
    "ProductSize"           VARCHAR(5)     NOT NULL,
    "ProductStyle"          VARCHAR(5)     NOT NULL,
    "ProductCost"           NUMERIC(10,4)  NOT NULL,
    "ProductPrice"          NUMERIC(10,2)  NOT NULL,
    scd_start_date          DATE           NOT NULL,
    scd_end_date            DATE,
    scd_is_current          BOOLEAN        NOT NULL,
    scd_version             SMALLINT       NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.fact_sales
-- Loaded via: dbt run (models/mart/fact_sales.sql), incremental
-- Grain: one row per (OrderNumber + OrderLineItem)
-- ----------------------------------------------------------------------------
CREATE TABLE mart.fact_sales (
    order_sk        CHAR(32)     NOT NULL,
    "OrderDate"     DATE         NOT NULL,
    "StockDate"     DATE         NOT NULL,
    "OrderNumber"   VARCHAR(20)  NOT NULL,
    "ProductKey"    INT          NOT NULL,
    "CustomerKey"   INT          NOT NULL,
    "TerritoryKey"  INT          NOT NULL,
    "OrderLineItem" SMALLINT     NOT NULL,
    "OrderQuantity" SMALLINT     NOT NULL,
    loaded_at       TIMESTAMP    NOT NULL,
    batch_id        VARCHAR(50)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- mart.fact_returns
-- Loaded via: dbt run (models/mart/fact_returns.sql), incremental
-- Grain: one row per (ReturnDate + TerritoryKey + ProductKey)
-- ----------------------------------------------------------------------------
CREATE TABLE mart.fact_returns (
    return_sk        CHAR(32)    NOT NULL,
    "ReturnDate"     DATE        NOT NULL,
    "TerritoryKey"   INT         NOT NULL,
    "ProductKey"     INT         NOT NULL,
    "ReturnQuantity" SMALLINT    NOT NULL,
    loaded_at        TIMESTAMP   NOT NULL,
    batch_id         VARCHAR(50) NOT NULL
);
