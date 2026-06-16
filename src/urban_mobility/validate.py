from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import pyarrow.parquet as pq

from urban_mobility.config import get_data_dir
from urban_mobility.download import validate_trip_request, zone_lookup_path
from urban_mobility.ingest import resolve_trip_path

MAX_TRIP_DURATION_MINUTES = 24 * 60
MAX_REASONABLE_SPEED_MPH = 100
AIRPORT_ZONE_IDS = (132, 138)

REQUIRED_COLUMNS = {
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "trip_distance",
    "fare_amount",
    "total_amount",
    "passenger_count",
    "PULocationID",
    "DOLocationID",
}


class ValidationError(RuntimeError):
    """Raised when validation inputs cannot be processed."""


@dataclass(frozen=True)
class ValidationResult:
    summary_path: Path
    validated_path: Path
    rejected_path: Path
    summary: dict[str, Any]


def validation_summary_path(data_dir: Path, year: int, month: int) -> Path:
    return data_dir / "reports" / "data_quality" / f"validation_{year}_{month:02d}.json"


def validated_trip_path(data_dir: Path, year: int, month: int, service: str) -> Path:
    return (
        data_dir
        / "processed"
        / "validated"
        / f"service={service}"
        / f"year={year}"
        / f"month={month:02d}"
        / "part-00000.parquet"
    )


def rejected_trip_path(data_dir: Path, year: int, month: int, service: str) -> Path:
    return (
        data_dir
        / "processed"
        / "rejected"
        / f"service={service}"
        / f"year={year}"
        / f"month={month:02d}"
        / "part-00000.parquet"
    )


def validate_trip_data(
    *,
    year: int,
    month: int,
    service: str,
    data_dir: Path | None = None,
    input_path: Path | None = None,
) -> ValidationResult:
    """Validate a Yellow Taxi Parquet file and write classified outputs."""
    validate_trip_request(year, month, service)
    resolved_data_dir = (data_dir or get_data_dir()).expanduser().resolve()
    source = (
        input_path.expanduser().resolve()
        if input_path
        else resolve_trip_path(resolved_data_dir, year, month, service)
    )
    zones = zone_lookup_path(resolved_data_dir)
    _validate_inputs(source, zones)
    columns = pq.read_schema(source).names
    zone_ids = _load_zone_ids(zones)

    validated = validated_trip_path(resolved_data_dir, year, month, service)
    rejected = rejected_trip_path(resolved_data_dir, year, month, service)
    summary_path = validation_summary_path(resolved_data_dir, year, month)
    for output in (validated, rejected, summary_path):
        output.parent.mkdir(parents=True, exist_ok=True)

    _remove_partition_files(validated.parent)
    _remove_partition_files(rejected.parent)

    ingested_at = datetime.now(UTC).replace(tzinfo=None, microsecond=0)
    with duckdb.connect() as connection:
        connection.execute("create temp table valid_zone_ids (location_id integer primary key)")
        connection.executemany(
            "insert into valid_zone_ids values (?)",
            [(zone_id,) for zone_id in sorted(zone_ids)],
        )
        connection.execute(
            _classification_sql(
                source=source,
                source_columns=columns,
                year=year,
                month=month,
                service=service,
                ingested_at=ingested_at,
            )
        )
        _copy_classification(connection, validated, "quality_status <> 'rejected'")
        _copy_classification(connection, rejected, "quality_status = 'rejected'")
        summary = _build_summary(
            connection=connection,
            source=source,
            validated=validated,
            rejected=rejected,
            year=year,
            month=month,
            service=service,
            validated_at=ingested_at,
        )

    _write_json(summary_path, summary)
    return ValidationResult(
        summary_path=summary_path,
        validated_path=validated,
        rejected_path=rejected,
        summary=summary,
    )


def _validate_inputs(source: Path, zones: Path) -> None:
    if not source.is_file():
        raise ValidationError(f"Trip Parquet file does not exist: {source}")
    if not zones.is_file():
        raise ValidationError(
            f"Taxi zone lookup does not exist: {zones}. "
            "Run the zone lookup download command before validation."
        )
    try:
        columns = set(pq.read_schema(source).names)
    except Exception as error:
        raise ValidationError(f"Unable to read Parquet schema: {source}") from error
    missing = sorted(REQUIRED_COLUMNS - columns)
    if missing:
        raise ValidationError(f"Trip Parquet is missing required columns: {', '.join(missing)}")


def _load_zone_ids(path: Path) -> set[int]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle)
            if not rows.fieldnames or "LocationID" not in rows.fieldnames:
                raise ValidationError("Taxi zone lookup is missing LocationID")
            zone_ids = {
                int(row["LocationID"])
                for row in rows
                if row.get("LocationID") and row["LocationID"].strip()
            }
    except (OSError, ValueError) as error:
        raise ValidationError(f"Unable to read taxi zone lookup: {path}") from error
    if not zone_ids:
        raise ValidationError(f"Taxi zone lookup contains no LocationID values: {path}")
    return zone_ids


def _classification_sql(
    *,
    source: Path,
    source_columns: list[str],
    year: int,
    month: int,
    service: str,
    ingested_at: datetime,
) -> str:
    normalized_columns = [
        "row_number() over () as source_row_number",
        _typed_column(source_columns, ("VendorID",), "bigint", "vendor_id"),
        _typed_column(
            source_columns,
            ("tpep_pickup_datetime",),
            "timestamp",
            "pickup_datetime",
        ),
        _typed_column(
            source_columns,
            ("tpep_dropoff_datetime",),
            "timestamp",
            "dropoff_datetime",
        ),
        _typed_column(source_columns, ("passenger_count",), "double", "passenger_count"),
        _typed_column(source_columns, ("trip_distance",), "double", "trip_distance"),
        _typed_column(source_columns, ("RatecodeID", "rate_code_id"), "integer", "rate_code_id"),
        _typed_column(
            source_columns,
            ("store_and_fwd_flag",),
            "varchar",
            "store_and_fwd_flag",
        ),
        _typed_column(source_columns, ("PULocationID",), "integer", "pickup_zone_id"),
        _typed_column(source_columns, ("DOLocationID",), "integer", "dropoff_zone_id"),
        _typed_column(source_columns, ("payment_type",), "integer", "payment_type"),
        _typed_column(source_columns, ("fare_amount",), "double", "fare_amount"),
        _typed_column(source_columns, ("extra",), "double", "extra"),
        _typed_column(source_columns, ("mta_tax",), "double", "mta_tax"),
        _typed_column(source_columns, ("tip_amount",), "double", "tip_amount"),
        _typed_column(source_columns, ("tolls_amount",), "double", "tolls_amount"),
        _typed_column(
            source_columns,
            ("improvement_surcharge",),
            "double",
            "improvement_surcharge",
        ),
        _typed_column(source_columns, ("total_amount",), "double", "total_amount"),
        _typed_column(
            source_columns,
            ("congestion_surcharge",),
            "double",
            "congestion_surcharge",
        ),
        _typed_column(source_columns, ("Airport_fee", "airport_fee"), "double", "airport_fee"),
    ]
    hash_columns = [
        "vendor_id",
        "pickup_datetime",
        "dropoff_datetime",
        "passenger_count",
        "trip_distance",
        "rate_code_id",
        "store_and_fwd_flag",
        "pickup_zone_id",
        "dropoff_zone_id",
        "payment_type",
        "fare_amount",
        "extra",
        "mta_tax",
        "tip_amount",
        "tolls_amount",
        "improvement_surcharge",
        "total_amount",
        "congestion_surcharge",
        "airport_fee",
    ]
    hash_parts = ",\n                    ".join(
        f"coalesce(cast({column} as varchar), '<NULL>')" for column in hash_columns
    )
    reason_cases = [
        ("missing_pickup_datetime", "pickup_datetime is null"),
        ("missing_dropoff_datetime", "dropoff_datetime is null"),
        (
            "pickup_after_dropoff",
            "pickup_datetime is not null and dropoff_datetime is not null "
            "and pickup_datetime > dropoff_datetime",
        ),
        (
            "duration_out_of_range",
            "duration_minutes is not null "
            f"and (duration_minutes < 0 or duration_minutes > {MAX_TRIP_DURATION_MINUTES})",
        ),
        ("missing_trip_distance", "trip_distance is null"),
        ("negative_trip_distance", "trip_distance < 0"),
        ("missing_fare_amount", "fare_amount is null"),
        ("negative_fare_amount", "fare_amount < 0"),
        ("missing_total_amount", "total_amount is null"),
        ("negative_total_amount", "total_amount < 0"),
        ("negative_passenger_count", "passenger_count < 0"),
        (
            "invalid_pickup_zone",
            "pickup_zone_id is null or not exists "
            "(select 1 from valid_zone_ids zones where zones.location_id = pickup_zone_id)",
        ),
        (
            "invalid_dropoff_zone",
            "dropoff_zone_id is null or not exists "
            "(select 1 from valid_zone_ids zones where zones.location_id = dropoff_zone_id)",
        ),
        (
            "unreasonable_average_speed",
            f"average_speed_mph > {MAX_REASONABLE_SPEED_MPH}",
        ),
    ]
    warning_cases = [
        (
            "zero_duration_positive_distance",
            "duration_minutes = 0 and trip_distance > 0",
        ),
    ]
    rejection_condition = " or\n                ".join(
        f"({condition})" for _, condition in reason_cases
    )
    quality_reasons = ",\n                ".join(
        [
            f"case when {condition} then '{name}' end"
            for name, condition in reason_cases + warning_cases
        ]
        + ["case when duplicate_rank > 1 then 'duplicate_record' end"]
    )
    warning_condition = " or ".join(
        [f"({condition})" for _, condition in warning_cases] + ["duplicate_rank > 1"]
    )
    source_literal = _sql_string(source.as_posix())
    service_literal = _sql_string(service)
    source_file_literal = _sql_string(str(source))
    ingested_literal = _sql_string(ingested_at.isoformat(sep=" "))
    airport_ids = ", ".join(str(zone_id) for zone_id in AIRPORT_ZONE_IDS)

    return f"""
        create temp table classified_trips as
        with normalized as (
            select
                {",\n                ".join(normalized_columns)}
            from read_parquet({source_literal})
        ),
        measured as (
            select
                *,
                date_diff('second', pickup_datetime, dropoff_datetime) / 60.0
                    as duration_minutes,
                case
                    when date_diff('second', pickup_datetime, dropoff_datetime) > 0
                    then trip_distance
                        / (date_diff('second', pickup_datetime, dropoff_datetime) / 3600.0)
                end as average_speed_mph,
                case
                    when trip_distance > 0 then total_amount / trip_distance
                end as revenue_per_mile
            from normalized
        ),
        hashed as (
            select
                *,
                md5(
                    concat_ws(
                        chr(31),
                        {hash_parts}
                    )
                ) as stable_record_hash
            from measured
        ),
        ranked as (
            select
                *,
                row_number() over (
                    partition by stable_record_hash order by source_row_number
                ) as duplicate_rank
            from hashed
        )
        select
            stable_record_hash
                || '-'
                || lpad(cast(duplicate_rank as varchar), 4, '0') as trip_id,
            stable_record_hash,
            source_row_number,
            vendor_id,
            pickup_datetime,
            dropoff_datetime,
            passenger_count,
            trip_distance,
            rate_code_id,
            store_and_fwd_flag,
            pickup_zone_id,
            dropoff_zone_id,
            payment_type,
            fare_amount,
            extra,
            mta_tax,
            tip_amount,
            tolls_amount,
            improvement_surcharge,
            total_amount,
            congestion_surcharge,
            airport_fee,
            duration_minutes,
            average_speed_mph,
            revenue_per_mile,
            pickup_zone_id in ({airport_ids}) or dropoff_zone_id in ({airport_ids})
                as is_airport_trip,
            case
                when {rejection_condition} then 'rejected'
                when {warning_condition} then 'warning'
                else 'valid'
            end as quality_status,
            concat_ws(
                '|',
                {quality_reasons}
            ) as quality_reasons,
            {service_literal} as service,
            {year}::integer as source_year,
            {month}::integer as source_month,
            {source_file_literal} as source_file,
            cast({ingested_literal} as timestamp) as ingested_at
        from ranked
    """


def _typed_column(
    source_columns: list[str],
    candidates: tuple[str, ...],
    data_type: str,
    alias: str,
) -> str:
    available = {column.casefold(): column for column in source_columns}
    source_name = next(
        (
            available[candidate.casefold()]
            for candidate in candidates
            if candidate.casefold() in available
        ),
        None,
    )
    if source_name is None:
        return f"cast(null as {data_type}) as {alias}"
    return f"try_cast({_quote_identifier(source_name)} as {data_type}) as {alias}"


def _quote_identifier(value: str) -> str:
    return f'"{value.replace('"', '""')}"'


def _sql_string(value: str) -> str:
    return f"'{value.replace("'", "''")}'"


def _copy_classification(
    connection: duckdb.DuckDBPyConnection,
    destination: Path,
    condition: str,
) -> None:
    connection.execute(
        f"""
        copy (
            select * exclude (service, source_year, source_month)
            from classified_trips
            where {condition}
        )
        to {_sql_string(destination.as_posix())}
        (format parquet, compression zstd)
        """
    )


def _build_summary(
    *,
    connection: duckdb.DuckDBPyConnection,
    source: Path,
    validated: Path,
    rejected: Path,
    year: int,
    month: int,
    service: str,
    validated_at: datetime,
) -> dict[str, Any]:
    status_counts = {"valid": 0, "warning": 0, "rejected": 0}
    for status, count in connection.execute(
        "select quality_status, count(*) from classified_trips group by quality_status"
    ).fetchall():
        status_counts[str(status)] = int(count)

    rule_counts = {
        str(reason): int(count)
        for reason, count in connection.execute(
            """
            select reason, count(*)
            from classified_trips,
                 unnest(string_split(quality_reasons, '|')) as reasons(reason)
            where reason <> ''
            group by reason
            order by reason
            """
        ).fetchall()
    }
    total_rows = sum(status_counts.values())
    return {
        "service": service,
        "year": year,
        "month": month,
        "source_path": str(source),
        "validated_at": validated_at.isoformat() + "Z",
        "total_rows": total_rows,
        "status_counts": status_counts,
        "rule_counts": rule_counts,
        "outputs": {
            "validated": str(validated),
            "rejected": str(rejected),
        },
    }


def _remove_partition_files(directory: Path) -> None:
    if not directory.exists():
        return
    for path in directory.glob("*.parquet"):
        path.unlink()


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate NYC TLC Yellow Taxi trip data.")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--month", type=int, required=True)
    parser.add_argument("--service", choices=("yellow",), default="yellow")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = validate_trip_data(
        year=arguments.year,
        month=arguments.month,
        service=arguments.service,
    )
    print(json.dumps(result.summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
