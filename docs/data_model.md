# Data Model

Persisted DuckDB inputs:

- `staging.yellow_trips`: validated valid/warning records with derived metrics and lineage
- `staging.taxi_zones`: normalized NYC TLC taxi zone lookup

dbt staging views:

- `stg_yellow_trips`
- `stg_taxi_zones`

Dimensions:

- `dim_zone`
- `dim_date`
- `dim_hour`
- `dim_payment_type`
- `dim_rate_code`

Fact:

- `fct_trips`: one row per loadable source-row occurrence with unique `trip_id`

Marts:

- `mart_daily_trip_metrics`
- `mart_hourly_demand`
- `mart_zone_demand`
- `mart_route_metrics`
- `mart_revenue_metrics`
- `mart_anomalous_trips`

`stable_record_hash` identifies equal source records. `trip_id` appends a deterministic
occurrence suffix so warning-classified duplicates remain traceable without violating fact
primary-key uniqueness. Zone, date, hour, payment, and rate relationships are enforced by dbt
tests.
