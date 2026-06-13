with src as (
    select * from {{ ref('snap_product') }}
)

select
    row_number() over (order by "ProductKey", dbt_valid_from) as product_sk,
    "ProductKey",
    "ProductSubcategoryKey",
    "ProductSKU",
    "ProductName",
    "ModelName",
    "ProductDescription",
    "ProductColor",
    "ProductSize",
    "ProductStyle",
    "ProductCost",
    "ProductPrice",
    dbt_valid_from::date as scd_start_date,
    dbt_valid_to::date as scd_end_date,
    (dbt_valid_to is null) as scd_is_current,
    (row_number() over (partition by "ProductKey" order by dbt_valid_from))::smallint as scd_version
from src
