select
    "ReturnDate"::date as "ReturnDate",
    "TerritoryKey",
    "ProductKey",
    "ReturnQuantity"::smallint as "ReturnQuantity",
    loaded_at,
    batch_id
from {{ source('staging', 'fact_returns') }}
