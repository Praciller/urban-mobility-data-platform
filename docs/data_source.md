# Data Source

The production-style source layout targets NYC TLC Yellow Taxi Trip Record Parquet files and the
NYC TLC Taxi Zone Lookup CSV.

```text
https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_YYYY-MM.parquet
https://d37ci6vzurychx.cloudfront.net/misc/taxi_zone_lookup.csv
```

The default portfolio demo does not require these remote files. It uses
`scripts/create_demo_fixture.py` to generate a tiny local Parquet fixture and taxi zone lookup
under `DATA_DIR`.

## Local Layout

```text
{DATA_DIR}/raw/tlc/taxi_zone_lookup.csv
{DATA_DIR}/raw/tlc/service=yellow/year=YYYY/month=MM/
{DATA_DIR}/sample/tlc/service=yellow/year=YYYY/month=MM/
{DATA_DIR}/processed/validated/service=yellow/year=YYYY/month=MM/
{DATA_DIR}/processed/rejected/service=yellow/year=YYYY/month=MM/
{DATA_DIR}/reports/data_quality/
```

## Offline Demo Fixture

PowerShell:

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
uv run python scripts/create_demo_fixture.py --year 2026 --month 1 --service yellow --sample-rows 1000
```

The fixture intentionally contains:

- one valid trip
- one duplicate warning trip
- one rejected trip with invalid amounts
- taxi zones required by the validation rules

This keeps tests, screenshots, and demo runs reproducible without an official dataset download.

## Optional Bounded Official Sample

For a networked local run, use a bounded sample:

```powershell
$env:DATA_DIR = "C:/data/urban-mobility-data-platform"
uv run python -m urban_mobility.download --year 2026 --month 1 --service yellow --sample-rows 1000
```

This does not download the full monthly file into the repository. It writes a bounded sample under
external `DATA_DIR/sample`. Remote sample creation may need DuckDB `httpfs` on first use.

## Validation

Validation checks required timestamps, amounts, passenger counts, trip duration, zones,
duplicates, and reasonable speed. Duplicate occurrences remain loadable with `warning` status;
impossible rows are written to rejected output.

```powershell
uv run python -m urban_mobility.ingest inspect --year 2026 --month 1 --service yellow --mode sample --sample-rows 1000
uv run python -m urban_mobility.validate --year 2026 --month 1 --service yellow
```

Downloads and fixture outputs are local files. CI uses generated temporary fixtures and never calls
the official TLC URLs.
