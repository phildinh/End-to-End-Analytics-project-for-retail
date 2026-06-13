-- ============================================================================
-- 01_create_staging_schema.sql
-- Staging schema — raw landing tables for the Python loader.
-- Natural keys only, no surrogate keys, no SCD columns.
-- Every table carries loaded_at + batch_id (added by loader/load_full.py
-- and loader/load_incremental.py).
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS staging;

-- ----------------------------------------------------------------------------
-- staging.fact_sales
-- Source: data/fact_sales_2020_2026.csv
-- ----------------------------------------------------------------------------
CREATE TABLE staging.fact_sales (
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
-- staging.fact_returns
-- Source: data/fact_returns_2020_2026.csv
-- ----------------------------------------------------------------------------
CREATE TABLE staging.fact_returns (
    "ReturnDate"     DATE        NOT NULL,
    "TerritoryKey"   INT         NOT NULL,
    "ProductKey"     INT         NOT NULL,
    "ReturnQuantity" SMALLINT    NOT NULL,
    loaded_at        TIMESTAMP   NOT NULL,
    batch_id         VARCHAR(50) NOT NULL
);

-- ----------------------------------------------------------------------------
-- staging.dim_customer
-- Source: data/AdventureWorks Customer Lookup.csv
-- ----------------------------------------------------------------------------
CREATE TABLE staging.dim_customer (
    "CustomerKey"    INT          NOT NULL,
    "Prefix"         VARCHAR(5),
    "FirstName"      VARCHAR(50)  NOT NULL,
    "LastName"       VARCHAR(50)  NOT NULL,
    "BirthDate"      DATE         NOT NULL,
    "MaritalStatus"  CHAR(1)      NOT NULL,
    "Gender"         CHAR(1),
    "EmailAddress"   VARCHAR(100) NOT NULL,
    "AnnualIncome"   INT          NOT NULL,
    "TotalChildren"  SMALLINT     NOT NULL,
    "EducationLevel" VARCHAR(30)  NOT NULL,
    "Occupation"     VARCHAR(30)  NOT NULL,
    "HomeOwner"      CHAR(1)      NOT NULL,
    loaded_at        TIMESTAMP    NOT NULL,
    batch_id         VARCHAR(50)  NOT NULL
);

-- ----------------------------------------------------------------------------
-- staging.dim_product
-- Source: data/AdventureWorks Product Lookup.csv
-- ----------------------------------------------------------------------------
CREATE TABLE staging.dim_product (
    "ProductKey"            INT            NOT NULL,
    "ProductSubcategoryKey" INT            NOT NULL,
    "ProductSKU"            VARCHAR(20)    NOT NULL,
    "ProductName"           VARCHAR(100)   NOT NULL,
    "ModelName"             VARCHAR(100)   NOT NULL,
    "ProductDescription"    VARCHAR(500)   NOT NULL,
    "ProductColor"          VARCHAR(20),
    "ProductSize"           VARCHAR(5)     NOT NULL,
    "ProductStyle"          VARCHAR(5)     NOT NULL,
    "ProductCost"           NUMERIC(10,4)  NOT NULL,
    "ProductPrice"          NUMERIC(10,2)  NOT NULL,
    loaded_at               TIMESTAMP      NOT NULL,
    batch_id                VARCHAR(50)    NOT NULL
);

-- ----------------------------------------------------------------------------
-- staging.dim_territory
-- Source: data/AdventureWorks Territory Lookup.csv
-- ----------------------------------------------------------------------------
CREATE TABLE staging.dim_territory (
    "SalesTerritoryKey" INT         NOT NULL,
    "Region"            VARCHAR(50) NOT NULL,
    "Country"           VARCHAR(50) NOT NULL,
    "Continent"         VARCHAR(20) NOT NULL,
    loaded_at           TIMESTAMP   NOT NULL,
    batch_id            VARCHAR(50) NOT NULL
);
