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
- **Per-partition cross-process writer lock:** local Windows byte-range locks and POSIX advisory locks prevent two validations/restores from publishing the same service/month concurrently. Contenders fail with a clear error instead of overwriting one another; the OS releases locks after a process dies. The persistent `publication.lock` file is never unlinked because removing it creates an inode-lock race. This local locking guarantee is **not** certified for network/shared filesystems.
- Atomic replacement covers process crashes at the pointer update; **physical power-loss durability on Windows, removable media and network filesystems is not certified**. Test the underlying filesystem's replacement guarantees before claiming crash consistency under hardware failure.
- `ValidationResult` paths now include a run revision rather than fixed legacy output names. Consumers must not construct versioned paths manually.

## Read-only inspection and guarded restore

`scripts/manage_publications.py` lists current/previous versions **without modifying data**. To deliberately restore an immutable previous revision, supply both the target and the exact currently observed revision. The tool rechecks the expected active version while holding the same partition lock; a mismatch or incomplete target is rejected.

```powershell
uv run python scripts/manage_publications.py --data-dir C:/data/urban-mobility-data-platform --year 2026 --month 1

# An operator must explicitly supply full 32-character lowercase revision IDs.
$previousRevision = "REPLACE_WITH_PREVIOUS_32_HEX_REVISION"
$observedActiveRevision = "REPLACE_WITH_CURRENT_32_HEX_REVISION"
uv run python scripts/manage_publications.py --data-dir C:/data/urban-mobility-data-platform --year 2026 --month 1 --restore $previousRevision --expect-current $observedActiveRevision
```

Restore moves only the pointer; all versions remain on disk. Do not use placeholder revision values literally. There is no automatic cleanup, no credential handling, and no modification to hosted deployments.

## Test evidence

- New tests simulate failure of pointer replacement, corrupt pointers, and incomplete versions; they verify that old published Parquet and summary data remain accessible.
- Cross-process tests verify that concurrent writers are refused, locks become available after a child publisher is killed, and separate monthly partitions can run independently.
- Restore tests verify the mandatory expected-current guard, invalid/missing target refusal, read-only default CLI, and precedence of an active snapshot over legacy reports.
- Existing Dagster, DuckDB, API, and integration tests must remain passing.
- Use `uv run pytest` and `uv run python scripts/benchmark_pipeline.py --rows 1000` to verify.

Future hardening: retention/garbage collection with a reviewed policy, multi-process read-consistency stress tests, and durable directory sync on supported POSIX filesystems.
