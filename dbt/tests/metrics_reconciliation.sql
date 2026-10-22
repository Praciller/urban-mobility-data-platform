-- Reconcile the curated fact with its fully-aggregated daily mart.
with facts as (
    select count(*)::bigint as trips, coalesce(sum(total_amount), 0)::double as revenue
    from {{ ref("fct_trips") }}
),
daily as (
    select coalesce(sum(trip_count), 0)::bigint as trips,
           coalesce(sum(total_revenue), 0)::double as revenue
    from {{ ref("mart_daily_trip_metrics") }}
)
select *
from facts cross join daily
where facts.trips <> daily.trips
   or abs(facts.revenue - daily.revenue) > 0.001
