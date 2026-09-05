# Hosted portfolio demo

Verified 2026-09-05 (Asia/Bangkok).

The public Render deployment is a bounded portfolio demo, not a live or realtime NYC transport service and not a production SLA.

## Source revision

- GitHub `main`: `9fb8c96f3684e4a98d133eb064b14b67a456074c`
- This revision is the one-commit successor to the earlier deployment pin `dcdcdbda964fd6ae3f5b38b4316112e009c52b46` and contains PR #20 Render-readiness hardening.
- The final PR-head CI for PR #20 completed successfully with all nine required checks.
- Repository ruleset `main-quality-gate` remained active and unchanged.

## Public services

- Dashboard: https://praciller-urban-mobility-dashboard.onrender.com
- API: https://praciller-urban-mobility-api.onrender.com
- OpenAPI: https://praciller-urban-mobility-api.onrender.com/openapi.json
- API docs: https://praciller-urban-mobility-api.onrender.com/docs

## Render resources

- API service: `praciller-urban-mobility-api`
- API service ID: `srv-dae4a6n40ujc73dopd50`
- Dashboard service: `praciller-urban-mobility-dashboard`
- Dashboard service ID: `srv-dae4b5740ujc73dot7ag`
- API plan/runtime/region: Free / Docker / Singapore
- Dashboard: free static site
- Database: none
- Persistent disk: none

The dashboard receives `VITE_API_BASE_URL` from the API service external URL. The API CORS configuration permits the exact hosted dashboard origin and keeps local development defaults separate.

## Data boundary

The hosted API image builds the deterministic offline demo during image creation. The deployment command passes `--sample-rows 1000`, but `create_demo_fixture.py` deliberately emits three synthetic Yellow Taxi rows for January 2026: one valid row, one duplicate warning retained for analytics, and one negative-fare row rejected by validation. Runtime storage is disposable and is not treated as durable state.

## Verification

Fresh hosted checks after deployment returned HTTP 200 for `/health`, `/openapi.json`, `/docs`, `/metadata`, `/quality/summary`, `/metrics/overview`, `/metrics/daily`, `/metrics/hourly-demand`, `/metrics/revenue`, `/zones`, `/routes/top`, and `/anomalies`. API responses included `X-Request-ID`.

A real Chromium session loaded the hosted dashboard directly, with no route mocking or local server. All seven pages were exercised at 1440px and 390px: Overview, Demand Trends, Zone Analytics, Route Analytics, Revenue Analytics, Anomaly Explorer, and Data Quality / Pipeline Status. The checks observed no horizontal overflow, application console errors, page errors, failed application requests, or localhost/127.0.0.1 traffic.

CORS preflight from `https://praciller-urban-mobility-dashboard.onrender.com` returned HTTP 200 with that exact `Access-Control-Allow-Origin`. A fake origin returned HTTP 400 with `Disallowed CORS origin`; wildcard CORS is not used.

## Rebuild proof

A clear-cache API deploy of the exact source revision completed live as Render deploy `dep-dae4f967bikc7382405g`. After that rebuild, health, metadata, overview, OpenAPI, CORS, desktop browser checks, and mobile browser checks were repeated successfully without manual seeding. This confirms the demo state is rebuilt into the image rather than relying on persistent runtime storage.

## Free-tier behavior and limitations

Render free services can spin down after inactivity, so the first request after an idle period can be slower. No cold-start duration was claimed because a controlled idle-period measurement was not performed in this verification session.

The sample is intentionally tiny and deterministic. It demonstrates pipeline, quality, serving, UI, and reproducibility behavior; it does not represent full NYC TLC scale or production availability.

## Redeploy / rollback

Normal redeploys should continue from reviewed `main` revisions through the existing `render.yaml` services. For recovery, select a previously verified Git revision and redeploy it through Render rather than mutating generated runtime data. Preserve the exact hosted dashboard origin in `CORS_ALLOWED_ORIGINS` when changing service URLs.
