{{
    config(
        materialized='incremental',
        unique_key='order_sk',
        incremental_strategy='delete+insert'
    )
}}

select
    {{ generate_surrogate_key(['"OrderNumber"', '"OrderLineItem"', '"OrderDate"']) }}::char(32) as order_sk,
    "OrderDate",
    "StockDate",
    "OrderNumber",
    "ProductKey",
    "CustomerKey",
    "TerritoryKey",
    "OrderLineItem",
    "OrderQuantity",
    loaded_at,
    batch_id
from {{ ref('stg_sales') }}

{% if is_incremental() %}
where loaded_at > coalesce((select max(loaded_at) from {{ this }}), '1900-01-01'::timestamp)
{% endif %}
