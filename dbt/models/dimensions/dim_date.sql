select distinct
    cast(pickup_datetime as date) as date,
    cast(strftime(pickup_datetime, '%Y%m%d') as integer) as date_key,
    extract(year from pickup_datetime)::integer as year,
    extract(month from pickup_datetime)::integer as month,
    monthname(pickup_datetime) as month_name,
    extract(day from pickup_datetime)::integer as day,
    dayname(pickup_datetime) as day_name,
    extract(isodow from pickup_datetime)::integer as iso_day_of_week,
    extract(isodow from pickup_datetime) in (6, 7) as is_weekend
from {{ ref("stg_yellow_trips") }}
