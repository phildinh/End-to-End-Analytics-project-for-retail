select
    "SalesTerritoryKey",
    "Region",
    "Country",
    "Continent",
    loaded_at,
    batch_id
from {{ source('staging', 'dim_territory') }}
