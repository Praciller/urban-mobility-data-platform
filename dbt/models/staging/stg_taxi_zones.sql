select
    cast(location_id as integer) as zone_id,
    cast(borough as varchar) as borough,
    cast(zone_name as varchar) as zone_name,
    cast(service_zone as varchar) as service_zone
from {{ source("mobility_staging", "taxi_zones") }}
