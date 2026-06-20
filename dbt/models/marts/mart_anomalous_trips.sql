select
    trip_id,
    service,
    pickup_datetime,
    dropoff_datetime,
    pickup_date,
    pickup_hour,
    pickup_zone_id,
    dropoff_zone_id,
    passenger_count,
    trip_distance,
    fare_amount,
    tip_amount,
    tolls_amount,
    total_amount,
    payment_type,
    rate_code_id,
    duration_minutes,
    average_speed_mph,
    revenue_per_mile,
    is_airport_trip,
    quality_status,
    quality_reasons,
    source_file,
    ingested_at
from {{ ref("fct_trips") }}
where
    quality_status = 'warning'
    or trip_distance = 0
    or duration_minutes = 0
    or average_speed_mph > 65
