select
    zone_id,
    borough,
    zone_name,
    service_zone,
    zone_id in (132, 138) as is_airport_zone
from {{ ref("stg_taxi_zones") }}
