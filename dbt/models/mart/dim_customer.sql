with src as (
    select * from {{ ref('snap_customer') }}
)

select
    row_number() over (order by "CustomerKey", dbt_valid_from) as customer_sk,
    "CustomerKey",
    "Prefix",
    "FirstName",
    "LastName",
    "BirthDate",
    "MaritalStatus",
    "Gender",
    "EmailAddress",
    "AnnualIncome",
    "TotalChildren",
    "EducationLevel",
    "Occupation",
    "HomeOwner",
    dbt_valid_from::date as scd_start_date,
    dbt_valid_to::date as scd_end_date,
    (dbt_valid_to is null) as scd_is_current,
    (row_number() over (partition by "CustomerKey" order by dbt_valid_from))::smallint as scd_version
from src
