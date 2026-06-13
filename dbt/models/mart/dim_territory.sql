with territory as (
    select * from {{ ref('stg_territory') }}
),

lat_long as (
    select * from (
        values
            (1,  47.6062,  -122.3321),
            (2,  40.7128,   -74.0060),
            (3,  39.8283,   -98.5795),
            (4,  33.4484,  -112.0740),
            (5,  33.7490,   -84.3880),
            (6,  45.4215,   -75.6972),
            (7,  48.8566,     2.3522),
            (8,  52.5200,    13.4050),
            (9,  52.2297,    21.0122),
            (10, 51.5074,    -0.1278),
            (11, -33.8688,  151.2093),
            (12, -37.8136,  144.9631),
            (13, -27.4698,  153.0251),
            (14, -36.8485,  174.7633),
            (15, -43.5321,  172.6362)
    ) as t ("SalesTerritoryKey", "Latitude", "Longitude")
)

select
    row_number() over (order by t."SalesTerritoryKey") as territory_sk,
    t."SalesTerritoryKey",
    t."Region",
    t."Country",
    t."Continent",
    ll."Latitude"::numeric(8,4) as "Latitude",
    ll."Longitude"::numeric(8,4) as "Longitude"
from territory t
left join lat_long ll on t."SalesTerritoryKey" = ll."SalesTerritoryKey"
