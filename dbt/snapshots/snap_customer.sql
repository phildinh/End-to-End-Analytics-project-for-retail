{% snapshot snap_customer %}

{{
    config(
      target_schema='staging',
      unique_key='"CustomerKey"',
      strategy='check',
      check_cols=['"AnnualIncome"', '"MaritalStatus"', '"HomeOwner"', '"Occupation"'],
    )
}}

select * from {{ ref('stg_customer') }}

{% endsnapshot %}
