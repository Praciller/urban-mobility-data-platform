# API

The FastAPI application reads the persisted DuckDB database in read-only mode. It exposes only
parameterized repository queries over dbt facts, dimensions, and marts. User-controlled sort
values are restricted to endpoint-specific allowlists.

## Start Locally

PowerShell:

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
$env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI is available at `http://127.0.0.1:8000/docs` and
`http://127.0.0.1:8000/openapi.json`.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /health` | Database availability, path, freshness, and mart status |
| `GET /metadata` | Supported services, date range, and key relation row counts |
| `GET /metrics/overview` | Trip, revenue, fare, duration, distance, airport, and warning KPIs |
| `GET /metrics/daily` | Paginated daily dbt mart metrics |
| `GET /metrics/hourly-demand` | Paginated demand by date and pickup hour |
| `GET /metrics/revenue` | Paginated daily revenue by payment type |
| `GET /zones` | Paginated zone attributes and pickup demand |
| `GET /zones/{zone_id}/summary` | Date-filtered pickup/dropoff summary for one zone |
| `GET /routes/top` | Paginated routes with zone names and aggregate metrics |
| `GET /anomalies` | Paginated explainable anomalous trips |
| `GET /exports/daily-metrics.csv` | Bounded daily aggregate CSV export |

Date-aware endpoints accept inclusive `start_date` and `end_date` values in `YYYY-MM-DD`
format. Relevant endpoints accept `zone_id`. List endpoints accept `limit`, `offset`,
`sort_by`, and `sort_order`; `limit` is restricted to 1 through 500.

The API returns `422` for invalid parameters/date order, `404` for unknown zones or empty
filtered result sets, and `503` when the DuckDB file or a required dbt relation is unavailable.
`/health` remains available during database outages and reports `status=unavailable`.
