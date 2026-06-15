# Architecture

The MVP is local-first. Raw NYC TLC files remain on the local filesystem, DuckDB performs
analytical processing, dbt builds documented marts, FastAPI serves metrics, and React renders
the dashboard. Local PostgreSQL is optional for future serving or metadata workloads.

```text
Official data -> downloader -> validation -> DuckDB -> dbt marts -> API -> dashboard
```

Phase 1 creates boundaries and configuration only. Runtime services arrive in later phases.
