# Backlog

This backlog captures future work after the local-demo MVP. It is intentionally not a commitment
to implement deployment, authentication, paid services, or new dataset services in Phase 8.

## Data Source Expansion

- Add Green Taxi and FHVHV support behind explicit service flags.
- Add month-range selection and safer backfill planning.
- Add local source-file inventory reports for multi-month runs.

## Data Quality

- Add out-of-month pickup/dropoff validation if analysts need strict monthly partitions.
- Add duplicate severity categories beyond the current warning behavior.
- Add richer rejected-row summaries by rule, zone, and source file.
- Add schema drift detection for future TLC column changes.

## Performance

- Add optional DuckDB indexes or pre-aggregated marts for larger local datasets.
- Add benchmark notes for dbt model runtime and API endpoint latency.
- Add CSV export limits tuned for larger local warehouses.

## Orchestration

- Migrate Dagster definition validation docs to `dg check defs` after compatibility is verified.
- Add clearer asset partition selection for multi-month local runs.
- Add runbook steps for failed materializations and reruns.
- Add optional local sensors only if they remain disabled by default.

## API

- Add explicit OpenAPI examples for each analytics endpoint.
- Add stronger pagination tests for large result sets.
- Add endpoint-level latency logging for local diagnostics.
- Add optional route filters for vendor, payment type, and airport trips.

## Frontend

- Add month and date range controls tied to available metadata.
- Add empty-state screenshots and loading-state examples.
- Add route drill-down views after API filters are expanded.
- Add chart-level accessibility review and keyboard navigation checks.

## Observability

- Add local structured logs for pipeline commands.
- Add lightweight run metadata summaries under ignored report paths.
- Add local-only error examples for demo troubleshooting.

## Deployment

- Keep deployment out of the MVP until local behavior is stable.
- If deployment is pursued later, evaluate generic PostgreSQL-compatible managed databases.
- Add container image versioning and runtime environment documentation.
- Keep cloud deployment optional and separate from the local demo.

## Security

- Expand secret-marker checks if new integrations are added.
- Add dependency audit commands for Python and Node.
- Keep API read-only unless a future requirements document explicitly approves writes.

## Portfolio Polish

- Capture a Dagster asset-graph screenshot; dashboard and FastAPI captures are complete.
- Add a short case-study page describing problem, architecture, and proof points.
- Add a release tag after final verification passes.
- Review GitHub topics, repo description, and README opening section before publishing.
