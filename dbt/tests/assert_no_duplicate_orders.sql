-- fact_sales must have exactly one row per (OrderNumber, OrderLineItem, OrderDate).
-- Note: OrderDate is part of the grain because the source data reuses some
-- (OrderNumber, OrderLineItem) pairs across different OrderDates (see
-- docs/architecture.md ADR-009).

select "OrderNumber", "OrderLineItem", "OrderDate", count(*) as row_count
from {{ ref('fact_sales') }}
group by "OrderNumber", "OrderLineItem", "OrderDate"
having count(*) > 1
