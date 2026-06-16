# Data Source

The planned primary source is official NYC TLC Yellow Taxi Trip Record data:

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
```

The Taxi Zone Lookup source is:

```text
https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

NYC TLC does not guarantee submitted record accuracy or completeness. The downloader preserves
full raw files under:

```text
{DATA_DIR}/raw/tlc/service=yellow/year=YYYY/month=MM/
```

Bounded development samples are stored separately:

```text
{DATA_DIR}/sample/tlc/service=yellow/year=YYYY/month=MM/
```

Validation writes loadable valid/warning rows and rejected rows separately:

```text
{DATA_DIR}/processed/validated/service=yellow/year=YYYY/month=MM/
{DATA_DIR}/processed/rejected/service=yellow/year=YYYY/month=MM/
{DATA_DIR}/reports/data_quality/validation_YYYY_MM.json
```

Required timestamp, amount, passenger, duration, zone, duplicate, and reasonable-speed checks
run before persisted loading. Duplicate occurrences remain loadable with `warning` status;
impossible rows are rejected.

Sample mode queries the remote Parquet file through DuckDB and writes only the requested rows.
CI never calls the official URL; tests generate tiny temporary Parquet fixtures.

PowerShell:

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
uv run python -m urban_mobility.download --year 2026 --month 1 --service yellow --sample-rows 1000
uv run python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow
uv run python -m urban_mobility.validate --year 2026 --month 1 --service yellow
```

Use `--force` only when an existing local file must be replaced. Downloads are written to a
temporary file and validated before replacing the destination.
