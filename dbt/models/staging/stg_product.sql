select
    "ProductKey",
    "ProductSubcategoryKey",
    "ProductSKU",
    "ProductName",
    "ModelName",
    "ProductDescription",
    coalesce("ProductColor", 'N/A') as "ProductColor",
    coalesce(nullif("ProductSize", '0'), 'N/A') as "ProductSize",
    coalesce(nullif("ProductStyle", '0'), 'N/A') as "ProductStyle",
    "ProductCost"::numeric(10,4) as "ProductCost",
    "ProductPrice"::numeric(10,2) as "ProductPrice",
    loaded_at,
    batch_id
from {{ source('staging', 'dim_product') }}
