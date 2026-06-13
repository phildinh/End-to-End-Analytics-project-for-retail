{{
    config(
        materialized='incremental',
        unique_key='return_sk',
        incremental_strategy='delete+insert'
    )
}}

with src as (
    select
        "ReturnDate",
        "TerritoryKey",
        "ProductKey",
        "ReturnQuantity",
        loaded_at,
        batch_id
    from {{ ref('stg_returns') }}

    {% if is_incremental() %}
    where loaded_at > coalesce((select max(loaded_at) from {{ this }}), '1900-01-01'::timestamp)
    {% endif %}
)

-- Source data can carry more than one return event for the same
-- (ReturnDate, TerritoryKey, ProductKey) — roll them up to the documented grain.
select
    {{ generate_surrogate_key(['"ReturnDate"', '"TerritoryKey"', '"ProductKey"']) }}::char(32) as return_sk,
    "ReturnDate",
    "TerritoryKey",
    "ProductKey",
    sum("ReturnQuantity")::smallint as "ReturnQuantity",
    max(loaded_at) as loaded_at,
    max(batch_id) as batch_id
from src
group by "ReturnDate", "TerritoryKey", "ProductKey"
