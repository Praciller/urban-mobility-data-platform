select
    pickup_date,
    count(*) as trip_count,
    coalesce(sum(passenger_count), 0)::double as passenger_count,
    sum(trip_distance) as trip_distance,
    sum(total_amount) as total_revenue,
    avg(duration_minutes) as average_duration_minutes,
    avg(average_speed_mph) as average_speed_mph,
    sum(case when is_airport_trip then 1 else 0 end) as airport_trip_count
from {{ ref("fct_trips") }}
group by pickup_date
