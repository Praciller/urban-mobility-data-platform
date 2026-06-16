select *
from {{ ref("fct_trips") }}
where
    quality_status = 'warning'
    or trip_distance = 0
    or duration_minutes = 0
    or average_speed_mph > 65
