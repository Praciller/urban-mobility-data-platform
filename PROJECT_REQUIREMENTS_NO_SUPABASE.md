# Urban Mobility Data Platform — Project Requirements

## 0. Repository Metadata

**Recommended repository name:** `urban-mobility-data-platform`

**Recommended GitHub description:**

> End-to-end urban mobility data engineering platform using NYC TLC taxi trip Parquet data, DuckDB/PostgreSQL, dbt, Dagster, FastAPI, and a React dashboard for ingestion, validation, analytics, anomaly detection, and production-style observability.

**Primary portfolio positioning:**

This project demonstrates production-grade Data Engineering and Analytics Engineering skills:
- public dataset ingestion
- raw/staging/mart data modeling
- data validation and quality reporting
- incremental pipeline orchestration
- analytical APIs
- dashboarding
- local-first Docker Compose setup
- CI-ready test suite
- observability and operational readiness

---

## 1. Project Goal

Build a local-first urban mobility analytics platform using official NYC Taxi & Limousine Commission trip record data.

The system must ingest monthly NYC TLC taxi trip Parquet files, validate and transform them, create analytical marts, expose metrics through FastAPI, and visualize insights through a web dashboard.

The project should look like a realistic production data platform, not a notebook-only demo.

---

## 2. Dataset

### 2.1 Primary Dataset

Use NYC TLC Trip Record Data.

Target data for MVP:
- Yellow Taxi Trip Records
- Start with one bounded month for local development, e.g. `2026-01`
- Support extension to multiple months and years

Official source pattern:

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
```

Example:

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2026-01.parquet
```

### 2.2 Dimension Dataset

Use Taxi Zone Lookup Table.

Official source:

```text
https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

### 2.3 Dataset Constraints

The system must:
- never commit raw Parquet files into Git
- download datasets into local `data/raw/`
- support deterministic sample mode for CI
- support full monthly mode for local analysis
- document that NYC TLC does not guarantee the accuracy/completeness of submitted trip records
- handle schema drift across years/months where possible

---

## 3. Target Users

### 3.1 Portfolio Reviewer

A recruiter, hiring manager, or senior engineer should be able to run the project locally and inspect:
- architecture
- pipeline quality
- data modeling
- API design
- dashboard
- tests
- operational behavior

### 3.2 Data Engineer

A data engineer should be able to:
- backfill a month
- rerun an idempotent pipeline
- inspect validation failures
- view data lineage
- query marts

### 3.3 Analyst / Business User

An analyst should be able to:
- inspect trip volume trends
- compare borough/zone demand
- analyze fare/revenue metrics
- identify anomalous trips
- export summary data

---

## 4. Recommended Stack

### 4.0 Explicit Database Constraint

Do **not** use Supabase for this project.

Allowed database/storage options:
- DuckDB for local analytical processing
- local PostgreSQL through Docker Compose
- generic managed PostgreSQL only as an optional future deployment path
- local filesystem for raw/processed data during MVP

Disallowed for this project:
- Supabase database
- Supabase auth
- Supabase storage
- Supabase edge functions
- any implementation that requires a Supabase account

The MVP must run fully locally without any external database SaaS account.


### 4.1 Local-First Core Stack

Use this stack for the MVP:

```text
Python 3.12
uv or Poetry
DuckDB
PostgreSQL
dbt-core + dbt-duckdb or dbt-postgres
Dagster
FastAPI
SQLAlchemy
Pydantic v2
Polars or pandas
PyArrow
Great Expectations or Soda Core
React + TypeScript + Vite
Recharts
Docker Compose
pytest
Ruff
GitHub Actions
```

### 4.2 Recommended Architecture Choice

Use **DuckDB as the local analytical engine** for the MVP.

Use PostgreSQL optionally for:
- API-serving database
- operational metadata
- production-like deployment path

Recommended MVP mode:

```text
Raw Parquet -> DuckDB staging -> dbt marts -> FastAPI reads DuckDB/mart outputs -> React dashboard
```

Recommended advanced mode:

```text
Raw Parquet -> DuckDB/Polars processing -> local PostgreSQL marts -> FastAPI -> React dashboard
```

Future deployment may use any standard PostgreSQL-compatible managed service, but the project must not include Supabase-specific code, configuration, SDKs, authentication, storage, or deployment instructions.

---

## 5. High-Level Architecture

```text
Official NYC TLC Dataset
        |
        v
Dataset Downloader
        |
        v
data/raw/tlc/year=YYYY/month=MM/*.parquet
        |
        v
Ingestion + Validation
        |
        v
DuckDB Staging Tables
        |
        v
dbt Models
        |
        +--> staging
        +--> dimensions
        +--> facts
        +--> marts
        |
        v
FastAPI Analytics API
        |
        v
React Dashboard
        |
        v
Portfolio Demo + README
```

---

## 6. Repository Structure

Create the repository with this structure:

```text
urban-mobility-data-platform/
  README.md
  PROJECT_REQUIREMENTS.md
  docker-compose.yml
  Makefile
  .env.example
  .gitignore
  pyproject.toml
  apps/
    api/
      app/
        __init__.py
        main.py
        core/
        routes/
        schemas/
        services/
        repositories/
      tests/
    web/
      package.json
      src/
        components/
        pages/
        lib/
        api/
  pipelines/
    dagster_project/
      pyproject.toml
      dagster_project/
        assets/
        jobs/
        resources/
        schedules/
  dbt/
    dbt_project.yml
    profiles.yml.example
    models/
      staging/
      intermediate/
      marts/
      dimensions/
      facts/
    tests/
    macros/
  src/
    urban_mobility/
      __init__.py
      config.py
      download.py
      ingest.py
      validate.py
      quality.py
      anomalies.py
      metrics.py
      utils.py
  data/
    raw/
      .gitkeep
    processed/
      .gitkeep
    sample/
      .gitkeep
  reports/
    data_quality/
      .gitkeep
    screenshots/
      .gitkeep
  docs/
    architecture.md
    data_source.md
    data_model.md
    api.md
    operations.md
    portfolio_review.md
  tests/
    unit/
    integration/
  .github/
    workflows/
      ci.yml
```

---

## 7. Functional Requirements

### 7.1 Dataset Download

The system must provide a CLI command:

```bash
python -m urban_mobility.download --year 2026 --month 1 --service yellow
```

The downloader must:
- construct the official NYC TLC Parquet URL
- download the file only if missing
- save to `data/raw/tlc/service=yellow/year=2026/month=01/yellow_tripdata_2026-01.parquet`
- verify file exists and is readable by PyArrow/DuckDB
- support `--force` to redownload
- support `--sample-rows` to create a smaller local sample
- download taxi zone lookup CSV if missing
- write download metadata to `data/processed/download_manifest.json`

Acceptance criteria:
- command downloads or reuses the file
- manifest records URL, local path, file size, timestamp, and checksum if feasible
- failure logs actionable error message

---

### 7.2 Raw Data Inspection

The system must provide:

```bash
python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow
```

It must output:
- row count
- column names
- inferred schema
- null counts for key fields
- min/max pickup datetime
- min/max dropoff datetime
- basic fare and distance stats

Acceptance criteria:
- output saved to `reports/data_quality/raw_profile_YYYY_MM.json`
- command works without loading entire file into memory when possible

---

### 7.3 Data Validation

Implement validation rules for raw trips:

Required checks:
- `tpep_pickup_datetime` is not null
- `tpep_dropoff_datetime` is not null
- pickup datetime <= dropoff datetime
- trip duration is between 0 minutes and 24 hours
- `trip_distance` >= 0
- `fare_amount` >= 0
- `total_amount` >= 0
- `passenger_count` >= 0 when present
- `PULocationID` is valid against taxi zone lookup
- `DOLocationID` is valid against taxi zone lookup
- remove or flag impossible records
- detect duplicate rows by stable hash

The system must classify records into:
- valid
- warning
- rejected

Acceptance criteria:
- validation summary saved to `reports/data_quality/validation_YYYY_MM.json`
- rejected rows saved to `data/processed/rejected/year=YYYY/month=MM/`
- warning rows remain loadable with quality flags

---

### 7.4 Data Modeling with dbt

Implement dbt models.

Required staging models:
- `stg_yellow_trips`
- `stg_taxi_zones`

Required dimension models:
- `dim_zone`
- `dim_date`
- `dim_hour`
- `dim_payment_type`
- `dim_rate_code`

Required fact models:
- `fct_trips`

Required marts:
- `mart_daily_trip_metrics`
- `mart_hourly_demand`
- `mart_zone_demand`
- `mart_route_metrics`
- `mart_revenue_metrics`
- `mart_anomalous_trips`

Minimum fields for `fct_trips`:
- trip_id
- pickup_datetime
- dropoff_datetime
- pickup_date
- pickup_hour
- pickup_zone_id
- dropoff_zone_id
- passenger_count
- trip_distance
- fare_amount
- tip_amount
- tolls_amount
- total_amount
- payment_type
- rate_code_id
- duration_minutes
- average_speed_mph
- revenue_per_mile
- is_airport_trip
- quality_status
- source_file
- ingested_at

Acceptance criteria:
- dbt run succeeds locally
- dbt tests pass
- models are documented with descriptions
- lineage graph is generated via dbt docs
- marts can be queried by FastAPI

---

### 7.5 Data Quality Tests

Add dbt tests:
- not null tests for primary keys
- uniqueness tests for `trip_id`
- accepted values for service type
- relationship tests from facts to dimensions
- positive values for distance/fare fields
- custom test for valid trip duration
- custom test for valid average speed range

Acceptance criteria:
- `dbt test` passes on sample mode
- failing checks produce readable output
- CI runs dbt tests on a small committed sample or generated fixture

---

### 7.6 Orchestration with Dagster

Implement Dagster assets:
- `taxi_zone_lookup`
- `raw_yellow_trip_file`
- `raw_trip_profile`
- `validated_trip_data`
- `dbt_models`
- `data_quality_report`
- `analytics_export`

Implement Dagster jobs:
- `monthly_tlc_ingestion_job`
- `sample_ingestion_job`
- `backfill_job`

Implement Dagster schedule:
- monthly schedule for new TLC data
- disabled by default in local dev

Acceptance criteria:
- Dagster UI starts locally
- sample job runs end-to-end
- failed asset logs clear error messages
- rerunning the same month is idempotent

---

### 7.7 Analytics API with FastAPI

Implement FastAPI endpoints:

```text
GET /health
GET /metadata
GET /metrics/overview
GET /metrics/daily
GET /metrics/hourly-demand
GET /metrics/revenue
GET /zones
GET /zones/{zone_id}/summary
GET /routes/top
GET /anomalies
GET /exports/daily-metrics.csv
```

Endpoint behavior:
- validate query parameters
- support date range filters
- support zone filters where relevant
- return typed Pydantic responses
- avoid returning raw huge datasets
- use pagination for list endpoints

Acceptance criteria:
- OpenAPI docs available
- pytest covers all endpoints
- API returns useful errors for invalid dates/zones
- `/health` includes data freshness metadata

---

### 7.8 Dashboard

Build a React dashboard with pages:

1. Overview
2. Demand Trends
3. Zone Analytics
4. Route Analytics
5. Revenue Analytics
6. Anomaly Explorer
7. Data Quality / Pipeline Status

Required visualizations:
- total trips KPI
- total revenue KPI
- average fare KPI
- average duration KPI
- trips by day
- trips by hour
- revenue by day
- top pickup zones
- top dropoff zones
- top routes
- anomaly table
- data quality summary

Acceptance criteria:
- dashboard runs locally
- handles API unavailable state
- handles loading and empty state
- uses TypeScript API clients
- charts are responsive
- includes portfolio-friendly screenshots in `reports/screenshots/`

---

### 7.9 Anomaly Detection

Implement deterministic anomaly rules first.

Required anomaly flags:
- negative amount
- zero distance with high fare
- extremely high average speed
- trip duration over 24 hours
- fare per mile above configurable threshold
- airport-like high fare pattern
- suspicious missing location

Optional ML anomaly detection:
- Isolation Forest over distance, duration, fare, fare_per_mile, pickup_hour
- save model only if deterministic behavior is documented

Acceptance criteria:
- anomalies are explainable
- anomaly reason is stored as text/code
- dashboard shows anomaly counts and examples
- no black-box anomaly score without reason

---

### 7.10 Export and Reproducibility

The system must export:
- validation reports as JSON
- summary marts as CSV
- API response examples
- generated schema docs
- screenshots

Acceptance criteria:
- full sample pipeline can be reproduced with one command
- generated files are excluded from Git unless intentionally small
- README documents commands exactly

---

## 8. Nonfunctional Requirements

### 8.1 Local-First and Free-Tier Constraint

The entire MVP must run locally without paid services.

Required:
- no paid APIs
- no cloud deployment required
- no database SaaS required
- no Supabase
- no proprietary BI tool required
- no external account required for local execution
- raw dataset downloaded from official public links

### 8.2 Performance

Targets:
- sample mode pipeline completes under 2 minutes
- one full month pipeline completes under 10 minutes on a normal laptop, if hardware allows
- API aggregate endpoints return under 500 ms on sample mode
- dashboard initial load under 3 seconds on sample mode
- avoid loading full Parquet files into memory unnecessarily

### 8.3 Idempotency

Pipeline reruns must:
- not duplicate rows
- not corrupt previous outputs
- overwrite or version reports deterministically
- detect already downloaded files
- allow `--force` only when explicitly requested

### 8.4 Observability

Implement:
- structured JSON logs
- request IDs in API logs
- pipeline run IDs
- validation report artifacts
- ingestion manifest
- API health endpoint with data freshness
- optional Prometheus metrics endpoint

### 8.5 Reliability

The system must:
- fail fast on invalid config
- retry transient downloads
- handle missing dataset month gracefully
- provide clear error messages
- never silently drop rejected records
- keep raw files immutable after download

### 8.6 Security

The system must:
- not commit `.env`
- not commit raw large datasets
- not expose local file paths in public API errors
- validate all API query parameters
- avoid arbitrary SQL execution from API inputs

### 8.7 Maintainability

Code must:
- use typed functions where practical
- separate ingestion, validation, modeling, API, and UI layers
- include docstrings for nontrivial pipeline logic
- keep business rules configurable
- include tests for critical transformations

### 8.8 CI/CD

GitHub Actions must run:
- Python lint
- Python tests
- frontend lint/build/test
- dbt parse/test on sample data
- minimal pipeline smoke test

CI must not download huge full datasets.

---

## 9. Environment and Configuration

Create `.env.example`:

```env
APP_ENV=local
DATA_DIR=./data
DUCKDB_PATH=./data/processed/urban_mobility.duckdb
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=urban_mobility
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
API_HOST=0.0.0.0
API_PORT=8000
WEB_PORT=5173
LOG_LEVEL=INFO
```

Configuration rules:
- `.env` is local-only and ignored by Git
- defaults must work in sample mode
- production-like settings must be documented but not required

---

## 10. Docker Compose Requirements

`docker-compose.yml` should provide:

Services:
- `api`
- `web`
- `postgres` optional
- `dagster-webserver`
- `dagster-daemon`
- `metabase` optional or omitted in MVP

Acceptance criteria:
- `docker compose up --build` starts the core services
- API is reachable
- web dashboard is reachable
- Dagster UI is reachable
- data volume is persisted locally

---

## 11. CLI Commands

Implement Makefile commands:

```makefile
setup
download-sample
profile-sample
validate-sample
dbt-run
dbt-test
pipeline-sample
api
web
dagster
test
lint
format
docker-up
docker-down
clean-generated
```

Acceptance criteria:
- `make pipeline-sample` runs the bounded local pipeline
- `make test` runs backend tests
- `make docker-up` starts local stack

---

## 12. Testing Requirements

### 12.1 Unit Tests

Cover:
- URL construction
- month/year formatting
- manifest creation
- trip duration calculation
- average speed calculation
- fare per mile calculation
- validation rules
- anomaly rules
- API schema validation

### 12.2 Integration Tests

Cover:
- sample file ingestion
- dbt model execution
- API reading from generated marts
- end-to-end sample pipeline

### 12.3 Frontend Tests

Cover:
- API unavailable state
- dashboard renders KPIs
- anomaly table renders
- loading state
- empty state

---

## 13. Documentation Requirements

Create these docs:

### 13.1 `README.md`

Must include:
- project overview
- architecture diagram
- stack
- dataset source
- quickstart
- local commands
- screenshots
- portfolio review path
- limitations
- future improvements

### 13.2 `docs/data_source.md`

Must include:
- official dataset description
- direct URL patterns
- taxi zone lookup source
- dataset limitations
- schema drift warning
- local sample mode explanation

### 13.3 `docs/data_model.md`

Must include:
- staging/fact/dimension/mart models
- lineage diagram
- table descriptions
- primary keys
- quality assumptions

### 13.4 `docs/operations.md`

Must include:
- how to backfill
- how to rerun
- how to inspect failures
- how to reset local generated data
- troubleshooting

### 13.5 `docs/portfolio_review.md`

Must include a reviewer path:
1. Start app
2. Run sample pipeline
3. Inspect Dagster job
4. Open dashboard overview
5. Open data quality page
6. Call API docs
7. Review dbt models/tests
8. Review CI workflow

---

## 14. MVP Scope

The first implementation must prioritize:

```text
1. Python package setup
2. Dataset downloader
3. Taxi zone lookup ingestion
4. Sample mode
5. DuckDB staging
6. dbt staging/fact/mart models
7. Validation reports
8. FastAPI overview metrics
9. React overview dashboard
10. Tests and README
```

Avoid overbuilding initially:
- no Kubernetes
- no Spark
- no paid cloud
- no real-time streaming
- no complex ML model first
- no auth first
- no multi-user app first

---

## 15. Stretch Goals

After MVP:
- add PostgreSQL serving mode
- add Dagster asset materialization UI screenshots
- add Prometheus metrics
- add Grafana dashboard
- add OpenTelemetry traces
- add Superset or Metabase dashboard
- add route-level geospatial visualization
- add multi-service support: yellow, green, FHV, HVFHV
- add monthly backfill across multiple years
- add cloud deployment guide
- add Great Expectations HTML docs
- add anomaly ML model with explainability

---

## 16. Success Criteria

The project is considered complete when:

```text
1. A reviewer can run the full sample pipeline with one command.
2. The system downloads or samples official NYC TLC data.
3. Data validation produces readable reports.
4. dbt models produce documented marts.
5. FastAPI exposes useful analytical endpoints.
6. React dashboard visualizes core metrics.
7. Tests pass locally and in CI.
8. README clearly explains architecture and trade-offs.
9. No paid service or external account is required for local MVP.
10. The project demonstrates production-grade data engineering, not just dashboarding.
```

---

## 17. Suggested Codex Execution Plan

Ask Codex to implement in phases.

### Phase 1 — Bootstrap

```text
Create the repository structure, Python package, pyproject.toml, .gitignore, .env.example, Makefile, and initial README. Do not implement all features yet. Keep the stack local-first and free.
```

### Phase 2 — Data Download and Profiling

```text
Implement NYC TLC downloader, taxi zone lookup downloader, manifest tracking, raw profile command, and unit tests. Use bounded sample mode for development.
```

### Phase 3 — DuckDB + dbt

```text
Implement DuckDB loading, dbt project, staging models, facts, dimensions, marts, and dbt tests. Ensure sample pipeline runs end-to-end.
```

### Phase 4 — FastAPI

```text
Implement FastAPI routes for health, metadata, overview metrics, daily metrics, zones, routes, revenue, and anomalies. Add tests.
```

### Phase 5 — Dashboard

```text
Implement React dashboard with overview, demand, revenue, zones, routes, anomalies, and data quality pages. Include loading/error states.
```

### Phase 6 — Dagster and CI

```text
Implement Dagster assets/jobs/schedules and GitHub Actions CI. CI must run only sample/smoke data, not full monthly downloads.
```

### Phase 7 — Documentation Polish

```text
Finalize README, docs, screenshots, architecture diagrams, data model docs, operations guide, and portfolio review path.
```

---

## 18. Implementation Constraints for Codex

Codex must follow these rules:

```text
1. Do not commit large raw data files.
2. Do not use paid services.
3. Do not require cloud accounts for MVP.
4. Do not use Supabase or any Supabase SDK/config/service.
4. Prefer deterministic sample mode.
5. Keep commands Windows PowerShell friendly when possible.
6. Keep architecture modular.
7. Add tests with each implementation phase.
8. Avoid notebook-only implementation.
9. Document every major trade-off.
10. Keep generated artifacts out of Git unless small and intentional.
```
