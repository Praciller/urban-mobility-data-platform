# Architecture

The platform is local-first. Files, reports, DuckDB databases, dbt outputs, Dagster storage, and
frontend builds stay out of Git. Full or long-running data work should use an external
`DATA_DIR`, for example `C:/data/urban-mobility-data-platform`.

## End-to-End Pipeline

```mermaid
flowchart LR
  A["NYC TLC Yellow Taxi source"] --> B["raw or sample Parquet under DATA_DIR"]
  Z["Taxi Zone Lookup CSV"] --> D["validation"]
  B --> C["raw profiling"]
  C --> D
  D --> E["validated Parquet"]
  D --> R["rejected Parquet and JSON quality report"]
  E --> F["DuckDB staging"]
  F --> G["dbt staging views"]
  G --> H["dimensions and fct_trips"]
  H --> I["dbt marts"]
  I --> J["FastAPI read-only analytics API"]
  J --> K["React dashboard"]
  I --> L["daily metrics CSV export"]
  M["Dagster local assets"] -. orchestrate .-> B
  M -. orchestrate .-> C
  M -. orchestrate .-> D
  M -. orchestrate .-> F
  M -. orchestrate .-> I
```

## Local Services

```mermaid
flowchart TB
  FS["Local filesystem DATA_DIR"] --> Duck["DuckDB database"]
  DBT["dbt CLI"] --> Duck
  Dag["Dagster dev server"] --> FS
  Dag --> DBT
  API["FastAPI on 127.0.0.1:8000"] --> Duck
  Web["React/Vite on 127.0.0.1:5173"] --> API
  Docs["dbt docs and project docs"] --> DBT
```

## Data Model Flow

```mermaid
flowchart LR
  S1["stg_yellow_trips"] --> F["fct_trips"]
  S2["stg_taxi_zones"] --> DZ["dim_zone"]
  S1 --> DD["dim_date"]
  S1 --> DH["dim_hour"]
  S1 --> DP["dim_payment_type"]
  S1 --> DR["dim_rate_code"]
  DZ --> F
  DD --> F
  DH --> F
  DP --> F
  DR --> F
  F --> M1["mart_daily_trip_metrics"]
  F --> M2["mart_hourly_demand"]
  F --> M3["mart_zone_demand"]
  F --> M4["mart_route_metrics"]
  F --> M5["mart_revenue_metrics"]
  F --> M6["mart_anomalous_trips"]
```

## Layer Boundaries

| Layer | Responsibility | Writes |
|---|---|---|
| Downloader/demo fixture | Materialize a bounded Parquet file and taxi zone lookup | `DATA_DIR/raw`, `DATA_DIR/sample` |
| Profiler | Produce metadata-first raw profile JSON | `DATA_DIR/reports/data_quality` |
| Validator | Classify valid, warning, and rejected rows | `DATA_DIR/processed`, `DATA_DIR/reports` |
| DuckDB loader | Idempotently replace one service/year/month in staging | `DUCKDB_PATH` |
| dbt | Build staging views, dimensions, fact, marts, tests, docs | DuckDB and `dbt/target` |
| FastAPI | Serve read-only analytics and CSV export | none |
| React dashboard | Read API data and render charts/tables | none |
| Dagster | Orchestrate existing pipeline code locally | `.dagster` metadata only |

## Design Decisions

- The API is read-only and does not expose arbitrary SQL or write endpoints.
- Validation and loading are idempotent for the same service/year/month.
- Dagster assets return small metadata dictionaries instead of large dataframes.
- The dashboard is intentionally decoupled from pipeline writes; it only reads the API.
- The default demo fixture avoids official dataset downloads and keeps the project reproducible.
