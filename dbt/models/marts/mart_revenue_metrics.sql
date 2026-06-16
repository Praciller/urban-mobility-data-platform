select
    pickup_date,
    payment_type,
    count(*) as trip_count,
    sum(fare_amount) as fare_revenue,
    sum(tip_amount) as tip_revenue,
    sum(tolls_amount) as tolls_revenue,
    sum(total_amount) as total_revenue,
    avg(revenue_per_mile) as average_revenue_per_mile
from {{ ref("fct_trips") }}
group by pickup_date, payment_type
