from __future__ import annotations

import json
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from urban_mobility.config import get_duckdb_path
from urban_mobility.download import trip_data_path, zone_lookup_path
from urban_mobility.load_duckdb import load_validated_to_duckdb
from urban_mobility.validate import validate_trip_data


def base_trip() -> dict[str, object]:
    return {
        "VendorID": 1,
        "tpep_pickup_datetime": datetime(2026, 1, 1, 8, 0),
        "tpep_dropoff_datetime": datetime(2026, 1, 1, 8, 30),
        "passenger_count": 1,
        "trip_distance": 3.0,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 1,
        "DOLocationID": 2,
        "payment_type": 1,
        "fare_amount": 18.0,
        "extra": 1.0,
        "mta_tax": 0.5,
        "tip_amount": 3.0,
        "tolls_amount": 0.0,
        "improvement_surcharge": 1.0,
        "total_amount": 23.5,
        "congestion_surcharge": 0.0,
        "Airport_fee": 0.0,
    }


def write_fixture(data_dir: Path, rows: list[dict[str, object]]) -> Path:
    source = trip_data_path(data_dir, 2026, 1, "yellow", sample=True, sample_rows=1000)
    source.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), source)

    zones = zone_lookup_path(data_dir)
    zones.parent.mkdir(parents=True, exist_ok=True)
    zones.write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "1,Manhattan,Alpha,Yellow Zone\n"
        "2,Queens,Beta,Boro Zone\n"
        "132,Queens,JFK Airport,Airports\n"
        "138,Queens,LaGuardia Airport,Airports\n",
        encoding="utf-8",
    )
    return source


def test_duckdb_path_defaults_under_data_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("DUCKDB_PATH", raising=False)

    assert get_duckdb_path() == tmp_path / "processed" / "urban_mobility.duckdb"

    configured = tmp_path / "warehouse" / "mobility.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(configured))
    assert get_duckdb_path() == configured


@pytest.mark.parametrize(
    ("mutate", "reason"),
    [
        (lambda row: row.update(tpep_pickup_datetime=None), "missing_pickup_datetime"),
        (lambda row: row.update(tpep_dropoff_datetime=None), "missing_dropoff_datetime"),
        (
            lambda row: row.update(
                tpep_dropoff_datetime=row["tpep_pickup_datetime"] - timedelta(minutes=1)
            ),
            "pickup_after_dropoff",
        ),
        (
            lambda row: row.update(
                tpep_dropoff_datetime=row["tpep_pickup_datetime"] + timedelta(hours=25)
            ),
            "duration_out_of_range",
        ),
        (lambda row: row.update(trip_distance=-1.0), "negative_trip_distance"),
        (lambda row: row.update(fare_amount=-1.0), "negative_fare_amount"),
        (lambda row: row.update(total_amount=-1.0), "negative_total_amount"),
        (lambda row: row.update(passenger_count=-1), "negative_passenger_count"),
        (lambda row: row.update(PULocationID=999), "invalid_pickup_zone"),
        (lambda row: row.update(DOLocationID=999), "invalid_dropoff_zone"),
        (
            lambda row: row.update(
                tpep_dropoff_datetime=row["tpep_pickup_datetime"] + timedelta(minutes=1),
                trip_distance=10.0,
            ),
            "unreasonable_average_speed",
        ),
    ],
)
def test_validation_rejects_required_rule_failures(
    tmp_path: Path,
    mutate: Callable[[dict[str, object]], None],
    reason: str,
) -> None:
    row = base_trip()
    mutate(row)
    source = write_fixture(tmp_path, [row])

    result = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        input_path=source,
    )

    assert result.summary["status_counts"]["rejected"] == 1
    rejected = pq.read_table(result.rejected_path)
    assert reason in rejected.column("quality_reasons")[0].as_py()


def test_validation_writes_classified_outputs_and_summary(tmp_path: Path) -> None:
    valid = base_trip()
    duplicate = valid.copy()
    invalid = base_trip()
    invalid["tpep_pickup_datetime"] = datetime(2026, 1, 2, 8, 0)
    invalid["tpep_dropoff_datetime"] = datetime(2026, 1, 2, 8, 30)
    invalid["fare_amount"] = -1.0
    source = write_fixture(tmp_path, [valid, duplicate, invalid])

    result = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        input_path=source,
    )

    assert result.summary["status_counts"] == {"valid": 1, "warning": 1, "rejected": 1}
    assert result.summary["rule_counts"]["duplicate_record"] == 1
    assert result.validated_path.parent == (
        tmp_path / "processed" / "validated" / "service=yellow" / "year=2026" / "month=01"
    )
    assert result.rejected_path.parent == (
        tmp_path / "processed" / "rejected" / "service=yellow" / "year=2026" / "month=01"
    )

    validated = pq.read_table(result.validated_path)
    assert validated.num_rows == 2
    assert sorted(validated.column("quality_status").to_pylist()) == ["valid", "warning"]
    assert len(set(validated.column("trip_id").to_pylist())) == 2
    assert len(set(validated.column("stable_record_hash").to_pylist())) == 1

    rejected = pq.read_table(result.rejected_path)
    assert rejected.num_rows == 1
    assert rejected.column("quality_status")[0].as_py() == "rejected"

    saved_summary = json.loads(result.summary_path.read_text(encoding="utf-8"))
    assert saved_summary["total_rows"] == 3
    assert saved_summary["outputs"]["validated"] == str(result.validated_path)


def test_zero_duration_with_positive_distance_is_warning(tmp_path: Path) -> None:
    row = base_trip()
    row["tpep_dropoff_datetime"] = row["tpep_pickup_datetime"]
    source = write_fixture(tmp_path, [row])

    result = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        input_path=source,
    )

    assert result.summary["status_counts"]["warning"] == 1
    validated = pq.read_table(result.validated_path)
    assert validated.column("quality_status")[0].as_py() == "warning"
    assert "zero_duration_positive_distance" in validated.column("quality_reasons")[0].as_py()


def test_duckdb_load_is_idempotent_for_service_month(tmp_path: Path) -> None:
    source = write_fixture(tmp_path, [base_trip()])
    validation = validate_trip_data(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        input_path=source,
    )
    database = tmp_path / "processed" / "test.duckdb"

    first = load_validated_to_duckdb(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        duckdb_path=database,
        validated_path=validation.validated_path,
    )
    second = load_validated_to_duckdb(
        year=2026,
        month=1,
        service="yellow",
        data_dir=tmp_path,
        duckdb_path=database,
        validated_path=validation.validated_path,
    )

    assert first.loaded_rows == 1
    assert second.loaded_rows == 1
    with duckdb.connect(str(database), read_only=True) as connection:
        trip_count = connection.execute("select count(*) from staging.yellow_trips").fetchone()
        zone_count = connection.execute("select count(*) from staging.taxi_zones").fetchone()
        month_count = connection.execute(
            """
            select count(*)
            from staging.yellow_trips
            where service = 'yellow' and source_year = 2026 and source_month = 1
            """
        ).fetchone()

    assert trip_count == (1,)
    assert zone_count == (4,)
    assert month_count == (1,)
