-- ============================================================================
-- 03_constraints_indexes.sql
-- Primary keys, foreign keys, and indexes for the mart schema, plus
-- watermark indexes on the staging fact tables.
--
-- NOTE on SCD2 dims: dim_customer and dim_product carry multiple historical
-- rows per natural key (CustomerKey / ProductKey), so those columns are not
-- unique and cannot be real FK targets. fact_sales.ProductKey/CustomerKey and
-- fact_returns.ProductKey are validated via dbt `relationships` tests
-- (filtered to scd_is_current = TRUE) instead of a DB-level FK constraint.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Primary keys
-- ----------------------------------------------------------------------------

ALTER TABLE mart.dim_product_category
    ADD CONSTRAINT pk_dim_product_category PRIMARY KEY ("ProductCategoryKey");

ALTER TABLE mart.dim_product_subcategory
    ADD CONSTRAINT pk_dim_product_subcategory PRIMARY KEY ("ProductSubcategoryKey");

ALTER TABLE mart.dim_territory
    ADD CONSTRAINT pk_dim_territory PRIMARY KEY (territory_sk);

ALTER TABLE mart.dim_calendar
    ADD CONSTRAINT pk_dim_calendar PRIMARY KEY ("Date");

ALTER TABLE mart.dim_customer
    ADD CONSTRAINT pk_dim_customer PRIMARY KEY (customer_sk);

ALTER TABLE mart.dim_product
    ADD CONSTRAINT pk_dim_product PRIMARY KEY (product_sk);

ALTER TABLE mart.fact_sales
    ADD CONSTRAINT pk_fact_sales PRIMARY KEY (order_sk);

ALTER TABLE mart.fact_returns
    ADD CONSTRAINT pk_fact_returns PRIMARY KEY (return_sk);

-- ----------------------------------------------------------------------------
-- Unique constraints needed as FK targets (natural keys with no SCD history)
-- ----------------------------------------------------------------------------

ALTER TABLE mart.dim_territory
    ADD CONSTRAINT uq_dim_territory_salesterritorykey UNIQUE ("SalesTerritoryKey");

-- ----------------------------------------------------------------------------
-- Foreign keys
-- ----------------------------------------------------------------------------

ALTER TABLE mart.dim_product_subcategory
    ADD CONSTRAINT fk_subcategory_category
    FOREIGN KEY ("ProductCategoryKey") REFERENCES mart.dim_product_category ("ProductCategoryKey");

ALTER TABLE mart.dim_product
    ADD CONSTRAINT fk_product_subcategory
    FOREIGN KEY ("ProductSubcategoryKey") REFERENCES mart.dim_product_subcategory ("ProductSubcategoryKey");

ALTER TABLE mart.fact_sales
    ADD CONSTRAINT fk_sales_territory
    FOREIGN KEY ("TerritoryKey") REFERENCES mart.dim_territory ("SalesTerritoryKey");

ALTER TABLE mart.fact_sales
    ADD CONSTRAINT fk_sales_calendar
    FOREIGN KEY ("OrderDate") REFERENCES mart.dim_calendar ("Date");

ALTER TABLE mart.fact_returns
    ADD CONSTRAINT fk_returns_territory
    FOREIGN KEY ("TerritoryKey") REFERENCES mart.dim_territory ("SalesTerritoryKey");

ALTER TABLE mart.fact_returns
    ADD CONSTRAINT fk_returns_calendar
    FOREIGN KEY ("ReturnDate") REFERENCES mart.dim_calendar ("Date");

-- ----------------------------------------------------------------------------
-- Indexes — staging watermark (incremental load filter on loaded_at)
-- ----------------------------------------------------------------------------

CREATE INDEX ix_staging_fact_sales_loaded_at ON staging.fact_sales (loaded_at);
CREATE INDEX ix_staging_fact_returns_loaded_at ON staging.fact_returns (loaded_at);

-- ----------------------------------------------------------------------------
-- Indexes — mart join columns (fact -> dim natural keys, used by Power BI
-- relationships and by dbt models even where no FK constraint exists)
-- ----------------------------------------------------------------------------

CREATE INDEX ix_fact_sales_productkey ON mart.fact_sales ("ProductKey");
CREATE INDEX ix_fact_sales_customerkey ON mart.fact_sales ("CustomerKey");
CREATE INDEX ix_fact_sales_territorykey ON mart.fact_sales ("TerritoryKey");
CREATE INDEX ix_fact_sales_orderdate ON mart.fact_sales ("OrderDate");

CREATE INDEX ix_fact_returns_productkey ON mart.fact_returns ("ProductKey");
CREATE INDEX ix_fact_returns_territorykey ON mart.fact_returns ("TerritoryKey");
CREATE INDEX ix_fact_returns_returndate ON mart.fact_returns ("ReturnDate");

-- ----------------------------------------------------------------------------
-- Indexes — SCD2 lookups (Power BI filters dims on scd_is_current = TRUE)
-- ----------------------------------------------------------------------------

CREATE INDEX ix_dim_customer_current ON mart.dim_customer ("CustomerKey") WHERE scd_is_current;
CREATE INDEX ix_dim_product_current ON mart.dim_product ("ProductKey") WHERE scd_is_current;
