select
    "CustomerKey",
    nullif(trim("Prefix"), '') as "Prefix",
    initcap("FirstName") as "FirstName",
    initcap("LastName") as "LastName",
    "BirthDate"::date as "BirthDate",
    "MaritalStatus",
    nullif("Gender", '') as "Gender",
    lower(trim("EmailAddress")) as "EmailAddress",
    "AnnualIncome"::int as "AnnualIncome",
    "TotalChildren"::smallint as "TotalChildren",
    "EducationLevel",
    "Occupation",
    "HomeOwner",
    loaded_at,
    batch_id
from {{ source('staging', 'dim_customer') }}
