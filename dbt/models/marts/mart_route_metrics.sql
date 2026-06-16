select
    pickup_zone_id,
    dropoff_zone_id,
    count(*) as trip_count,
    avg(trip_distance) as average_trip_distance,
    avg(duration_minutes) as average_duration_minutes,
    sum(total_amount) as total_revenue
from {{ ref("fct_trips") }}
group by pickup_zone_id, dropoff_zone_id
