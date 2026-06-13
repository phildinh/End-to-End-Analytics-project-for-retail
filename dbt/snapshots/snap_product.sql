{% snapshot snap_product %}

{{
    config(
      target_schema='staging',
      unique_key='"ProductKey"',
      strategy='check',
      check_cols=['"ProductCost"', '"ProductPrice"'],
    )
}}

select * from {{ ref('stg_product') }}

{% endsnapshot %}
