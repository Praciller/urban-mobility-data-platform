-- Every validated duplicate remains discoverable in the anomaly mart,
-- without contributing to business aggregates.
select stage.trip_id
from {{ ref("stg_yellow_trips") }} as stage
left join {{ ref("mart_anomalous_trips") }} as anomalies
    on stage.trip_id = anomalies.trip_id
where list_contains(
    string_split(coalesce(stage.quality_reasons, ''), '|'),
    'duplicate_record'
)
and anomalies.trip_id is null
