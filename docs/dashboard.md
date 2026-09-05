# Dashboard

The Phase 5 dashboard is a local React + TypeScript Vite app in `apps/web`. It reads the
existing FastAPI analytics API and does not create, update, or delete backend data.

## Local Run

```powershell
uv run uvicorn apps.api.app.main:app --reload --host 127.0.0.1 --port 8000
cd apps/web
npm install
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev -- --host 127.0.0.1
```

## Pages

- Overview
- Demand Trends
- Zone Analytics
- Route Analytics
- Revenue Analytics
- Anomaly Explorer
- Data Quality / Pipeline Status

## API Surface

Dashboard fetches are centralized in `apps/web/src/api/client.ts` and target:

- `/health`
- `/metadata`
- `/quality/summary`
- `/metrics/overview`
- `/metrics/daily`
- `/metrics/hourly-demand`
- `/metrics/revenue`
- `/zones`
- `/zones/{zone_id}/summary`
- `/routes/top`
- `/anomalies`
- `/exports/daily-metrics.csv`

List endpoint `404` responses are converted to empty page states so a clean dataset with no
anomalies remains reviewable. The quality summary is optional until the first demo run.

## Verification

```powershell
cd apps/web
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
npm audit --audit-level=high
npm run e2e:install
npm run e2e
```

`npm run e2e` uses a generated local sample fixture, a temporary DuckDB path, and Playwright
Chromium projects for desktop and mobile. It exercises health/KPI/page navigation, visible filter
requests, anomaly and data-quality evidence, API failure/retry recovery, compact navigation, and
mobile overflow. Traces, screenshots, videos, and the HTML report remain ignored local/CI output.
