# Immutable Validation Publication — Local Snapshot Protocol

The 2026-10-22 hardening replaces the previous **three sequential file overwrites** with a single active pointer to an immutable run directory. This protects consumers from seeing mixed validated/rejected/summary artifacts after an ordinary process interruption.

## On-disk layout

```text
DATA_DIR/processed/publications/service=yellow/year=2026/month=01/
  current.json               # schema_version=1, revision=<32 lowercase hex characters>
  versions/
    <revision-A>/
      validated.parquet
      rejected.parquet
      summary.json
    <revision-B>/
      validated.parquet
      rejected.parquet
      summary.json
```

`activate_version()` flushes every complete artifact, writes and fsyncs a temporary pointer in the same directory as `current.json`, and atomically replaces the pointer. The directory of the current revision is never modified. When preparation fails, the previous pointer and files remain unchanged. When a process crashes **before** pointer replacement, a version may be orphaned but remains invisible; when the pointer is replaced, the complete referenced snapshot exists.

`validated_trip_path()`, `rejected_trip_path()`, and `validation_summary_path()` now resolve the active immutable version. The FastAPI quality repository looks up active version pointers as well as older, flat legacy reports. Data loaded into DuckDB is transactional at the selected month partition.

## Compatibility and operator boundaries

- **No forced migration of legacy data.** When a partition has no `current.json`, old flat validated/rejected paths still resolve, and old report JSONs remain readable.
- After the first successful new run of a partition, its `current.json` is the authoritative location. An invalid or incomplete pointer raises an error rather than silently using a stale legacy copy.
- Existing DBT/DuckDB reads are unaffected after loading; a loader with an explicit `validated_path` continues to use that pinned immutable revision.
- **Do not automatically delete old versions.** Other readers or a manual recovery may still use them. Review any unreferenced run folders before explicit cleanup.
- **A single read of the manifest provides one snapshot.** Independent path resolver calls made across a simultaneous activation may each resolve a different *complete* revision; pin a revision path for multi-artifact processing.
- Last completed publisher wins if two writers target the same partition. Do not schedule concurrent writers without orchestration-level partition locking.
- Atomic replacement covers process crashes at the pointer update; **physical power-loss durability on Windows, removable media and network filesystems is not certified**. Test the underlying filesystem's replacement guarantees before claiming crash consistency under hardware failure.
- `ValidationResult` paths now include a run revision rather than fixed legacy output names. Consumers must not construct versioned paths manually.

## Test evidence

- New tests simulate failure of the pointer replacement, corrupt pointers, and incomplete versions; they verify that old published Parquet and summary data remain accessible.
- Existing Dagster, DuckDB, API, and integration tests must remain passing.
- Use `uv run pytest` and `uv run python scripts/benchmark_pipeline.py --rows 1000` to verify.

Future hardening: explicit per-partition publish lock, recovery/garbage-collection tooling with a reviewed retention policy, multi-process read-consistency stress tests, and durable directory sync on supported POSIX filesystems.
