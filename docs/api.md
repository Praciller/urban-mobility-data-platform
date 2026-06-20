# API

FastAPI serves read-only analytics from persisted DuckDB/dbt marts. It does not create, update, or
delete data. Sort fields are allowlisted per endpoint and all user filters are parameterized.

## Start Locally

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
$env:DUCKDB_PATH = "$env:DATA_DIR/processed/urban_mobility.duckdb"
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
```

OpenAPI:

- `http://127.0.0.1:8000/docs`
- `http://127.0.0.1:8000/openapi.json`

## Endpoint Map

| Endpoint | Purpose |
|---|---|
| `GET /health` | Database availability, freshness, and mart status |
| `GET /metadata` | Supported services, date range, and row counts |
| `GET /quality/summary` | Latest sanitized validation counts, rules, and artifact name |
| `GET /metrics/overview` | Trip, revenue, fare, duration, distance, airport, and warning KPIs |
| `GET /metrics/daily` | Paginated daily metrics |
| `GET /metrics/hourly-demand` | Paginated demand by pickup date and hour |
| `GET /metrics/revenue` | Paginated revenue by date and payment type |
| `GET /zones` | Zone attributes and pickup demand |
| `GET /zones/{zone_id}/summary` | Pickup/dropoff summary for one zone |
| `GET /routes/top` | Top origin/destination route metrics |
| `GET /anomalies` | Explainable warning trips |
| `GET /exports/daily-metrics.csv` | Bounded daily metrics CSV export |

## Filters

Date-aware endpoints accept inclusive `start_date` and `end_date` values in `YYYY-MM-DD` format.
Relevant endpoints accept `zone_id`. List endpoints accept `limit`, `offset`, `sort_by`, and
`sort_order`; `limit` is restricted to 1 through 500.

Examples:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/metadata
Invoke-RestMethod http://127.0.0.1:8000/quality/summary
Invoke-RestMethod "http://127.0.0.1:8000/metrics/daily?limit=10"
Invoke-RestMethod "http://127.0.0.1:8000/routes/top?limit=5&sort_by=trip_count&sort_order=desc"
```

## Error Behavior

| Status | Meaning |
|---|---|
| `422` | Invalid parameter, invalid date order, or invalid sorting value |
| `404` | Unknown zone or empty filtered result set |
| `503` | DuckDB file or required dbt relation is unavailable |

`/quality/summary` returns `404` before the first validation run and `503` if the latest summary
is malformed, unreadable, or exceeds the 1 MB safety limit. Its response excludes source and
output paths.

`/health` remains available during database outages and reports `status=unavailable` or
`status=degraded` with missing mart details.

Browser CORS is restricted to the default local Vite origins, `http://localhost:5173` and
`http://127.0.0.1:5173`. The public health response does not expose the local DuckDB path.

## Dashboard Contract

The React dashboard consumes only the endpoints listed above. API calls are centralized in
`apps/web/src/api/client.ts`, and the dashboard is configured with `VITE_API_BASE_URL`.
