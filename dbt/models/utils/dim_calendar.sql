with spine as (
    {{ dbt_utils.date_spine(
        datepart="day",
        start_date="cast('2020-01-01' as date)",
        end_date="cast('2027-01-01' as date)"
    ) }}
)

select
    date_day::date as "Date",
    to_char(date_day, 'YYYYMMDD')::int as "DateKey",
    extract(year from date_day)::smallint as "Year",
    extract(quarter from date_day)::smallint as "QuarterNumber",
    'Q' || extract(quarter from date_day)::text as "QuarterName",
    extract(month from date_day)::smallint as "MonthNumber",
    trim(to_char(date_day, 'Month')) as "MonthName",
    trim(to_char(date_day, 'Mon')) as "MonthShort",
    extract(week from date_day)::smallint as "WeekNumber",
    extract(isodow from date_day)::smallint as "DayOfWeek",
    trim(to_char(date_day, 'Day')) as "DayName",
    trim(to_char(date_day, 'Dy')) as "DayShort",
    (extract(isodow from date_day) in (6, 7)) as "IsWeekend",
    (extract(isodow from date_day) not in (6, 7)) as "IsWeekday",
    to_char(date_day, 'Mon YYYY') as "MonthYear",
    to_char(date_day, 'YYYYMM')::int as "YearMonth"
from spine
