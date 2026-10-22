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
from {{ ref("stg_yellow_trips") }}
-- Preserve duplicate occurrences in staging/quality but exclude them from
-- business KPIs: a duplicate source row is not another passenger trip.
where not list_contains(
    string_split(coalesce(quality_reasons, ''), '|'),
    'duplicate_record'
)
