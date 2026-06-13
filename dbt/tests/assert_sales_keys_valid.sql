-- fact_sales.CustomerKey / ProductKey must match a current (scd_is_current) row
-- in dim_customer / dim_product. SCD2 history means these are not enforceable
-- as DB foreign keys (see ADR-008), so they are validated here instead.

select fs."CustomerKey"
from {{ ref('fact_sales') }} fs
left join {{ ref('dim_customer') }} dc
    on fs."CustomerKey" = dc."CustomerKey"
    and dc.scd_is_current
where dc."CustomerKey" is null

union all

select fs."ProductKey"
from {{ ref('fact_sales') }} fs
left join {{ ref('dim_product') }} dp
    on fs."ProductKey" = dp."ProductKey"
    and dp.scd_is_current
where dp."ProductKey" is null
