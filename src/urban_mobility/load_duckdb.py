from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import duckdb

from urban_mobility.config import get_data_dir, get_duckdb_path
from urban_mobility.download import validate_trip_request, zone_lookup_path
from urban_mobility.validate import validated_trip_path


class DuckDBLoadError(RuntimeError):
    """Raised when validated data cannot be loaded into DuckDB."""


@dataclass(frozen=True)
class DuckDBLoadResult:
    duckdb_path: Path
    loaded_rows: int
    zone_rows: int


def load_validated_to_duckdb(
    *,
    year: int,
    month: int,
    service: str,
    data_dir: Path | None = None,
    duckdb_path: Path | None = None,
    validated_path: Path | None = None,
) -> DuckDBLoadResult:
    """Replace one validated service/month partition in persisted DuckDB staging."""
    validate_trip_request(year, month, service)
    resolved_data_dir = (data_dir or get_data_dir()).expanduser().resolve()
    database = (duckdb_path or get_duckdb_path()).expanduser().resolve()
    trips = (
        validated_path.expanduser().resolve()
        if validated_path
        else validated_trip_path(resolved_data_dir, year, month, service)
    )
    zones = zone_lookup_path(resolved_data_dir)
    if not trips.is_file():
        raise DuckDBLoadError(
            f"Validated Parquet does not exist: {trips}. Run validation before loading DuckDB."
        )
    if not zones.is_file():
        raise DuckDBLoadError(f"Taxi zone lookup does not exist: {zones}")

    database.parent.mkdir(parents=True, exist_ok=True)
    trip_literal = _sql_string(trips.as_posix())
    zone_literal = _sql_string(zones.as_posix())
    service_literal = _sql_string(service)
    staged_select = f"""
        select
            *,
            {service_literal}::varchar as service,
            {year}::integer as source_year,
            {month}::integer as source_month
        from read_parquet({trip_literal}, hive_partitioning = false)
    """
    with duckdb.connect(str(database)) as connection:
        try:
            connection.execute("begin transaction")
            connection.execute("create schema if not exists staging")
            connection.execute(
                f"""
                create or replace table staging.taxi_zones as
                select
                    try_cast(LocationID as integer) as location_id,
                    cast(Borough as varchar) as borough,
                    cast(Zone as varchar) as zone_name,
                    cast(service_zone as varchar) as service_zone
                from read_csv_auto({zone_literal}, header = true)
                where try_cast(LocationID as integer) is not null
                """
            )
            connection.execute(
                f"""
                create table if not exists staging.yellow_trips as
                select * from ({staged_select}) where false
                """
            )
            connection.execute(
                """
                delete from staging.yellow_trips
                where service = ? and source_year = ? and source_month = ?
                """,
                [service, year, month],
            )
            connection.execute(f"insert into staging.yellow_trips {staged_select}")
            loaded_rows = connection.execute(
                """
                select count(*)
                from staging.yellow_trips
                where service = ? and source_year = ? and source_month = ?
                """,
                [service, year, month],
            ).fetchone()[0]
            zone_rows = connection.execute("select count(*) from staging.taxi_zones").fetchone()[0]
            connection.execute("commit")
        except Exception as error:
            connection.execute("rollback")
            raise DuckDBLoadError(f"Unable to load validated data into {database}") from error

    return DuckDBLoadResult(
        duckdb_path=database,
        loaded_rows=int(loaded_rows),
        zone_rows=int(zone_rows),
    )


def _sql_string(value: str) -> str:
    return f"'{value.replace("'", "''")}'"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load validated trips into persisted DuckDB.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--service", choices=("yellow",), default="yellow")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = load_validated_to_duckdb(
        year=arguments.year,
        month=arguments.month,
        service=arguments.service,
    )
    print(
        f"Loaded {result.loaded_rows} trip row(s) and {result.zone_rows} zone row(s) "
        f"into {result.duckdb_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
