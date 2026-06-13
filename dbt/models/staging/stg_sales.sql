select
    "OrderDate"::date as "OrderDate",
    "StockDate"::date as "StockDate",
    "OrderNumber",
    "ProductKey",
    "CustomerKey",
    "TerritoryKey",
    "OrderLineItem"::smallint as "OrderLineItem",
    "OrderQuantity"::smallint as "OrderQuantity",
    loaded_at,
    batch_id
from {{ source('staging', 'fact_sales') }}
