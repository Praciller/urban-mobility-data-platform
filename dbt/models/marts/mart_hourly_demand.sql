select
    pickup_date,
    pickup_hour,
    count(*) as trip_count,
    sum(passenger_count) as passenger_count,
    avg(duration_minutes) as average_duration_minutes,
    sum(total_amount) as total_revenue
from {{ ref("fct_trips") }}
group by pickup_date, pickup_hour
