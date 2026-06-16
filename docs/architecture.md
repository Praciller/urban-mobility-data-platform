# Architecture

The MVP is local-first. Raw NYC TLC files remain on the local filesystem, DuckDB performs
analytical processing, dbt builds documented marts, FastAPI serves metrics, and React renders
the dashboard. Local PostgreSQL is optional for future serving or metadata workloads.

```text
Official data -> downloader -> validation -> DuckDB -> dbt marts -> API -> dashboard
```

Phase 3 implements the pipeline through dbt marts. Validation runs in an in-process DuckDB
connection and writes classified Parquet artifacts. A separate transactional loader replaces
one service/year/month partition in the persisted DuckDB `staging` schema, then dbt builds
typed staging views, dimensions, `fct_trips`, and aggregate marts in the `main` schema.

Phase 4 adds synchronous FastAPI handlers backed by short-lived read-only DuckDB connections.
Route handlers validate HTTP parameters, the service layer enforces cross-field rules, and the
repository owns parameterized SQL plus relation checks. The API is read-only and never accepts
arbitrary SQL.

React and Dagster remain later-phase boundaries.
