select
    trip_id,
    service,
    pickup_datetime,
    dropoff_datetime,
    cast(pickup_datetime as date) as pickup_date,
    extract(hour from pickup_datetime)::integer as pickup_hour,
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
-- Use staging so duplicate warnings remain visible in the Anomaly Explorer
-- even though curated facts exclude them from aggregate metrics.
from {{ ref("stg_yellow_trips") }}
where
    quality_status = 'warning'
    or trip_distance = 0
    or duration_minutes = 0
    or average_speed_mph > 65
