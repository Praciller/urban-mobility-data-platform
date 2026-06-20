select
    pickup_zone_id as zone_id,
    count(*) as pickup_trip_count,
    coalesce(sum(passenger_count), 0)::double as passenger_count,
    sum(total_amount) as total_revenue,
    avg(trip_distance) as average_trip_distance
from {{ ref("fct_trips") }}
group by pickup_zone_id
