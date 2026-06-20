from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.parquet as pq

from urban_mobility.config import get_data_dir
from urban_mobility.download import (
    DEFAULT_SAMPLE_ROWS,
    trip_data_path,
    validate_trip_request,
    zone_lookup_path,
)


def create_demo_fixture(
    *,
    data_dir: Path,
    year: int,
    month: int,
    service: str,
    sample_rows: int,
) -> dict[str, Any]:
    validate_trip_request(year, month, service)
    if sample_rows <= 0:
        raise ValueError("sample_rows must be greater than zero")

    trip_path = trip_data_path(
        data_dir,
        year,
        month,
        service,
        sample=True,
        sample_rows=sample_rows,
    )
    rows = _demo_rows(year, month)
    trip_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(pa.Table.from_pylist(rows), trip_path)

    zones = zone_lookup_path(data_dir)
    zones.parent.mkdir(parents=True, exist_ok=True)
    zones.write_text(
        "LocationID,Borough,Zone,service_zone\n"
        "1,Manhattan,Alpha,Yellow Zone\n"
        "132,Queens,JFK Airport,Airports\n"
        "138,Queens,LaGuardia Airport,Airports\n",
        encoding="utf-8",
    )

    return {
        "service": service,
        "year": year,
        "month": month,
        "sample_rows": sample_rows,
        "trip_path": str(trip_path),
        "zone_lookup_path": str(zones),
        "trip_row_count": len(rows),
    }


def _demo_rows(year: int, month: int) -> list[dict[str, object]]:
    valid = _base_row(year, month)
    duplicate_warning = valid.copy()
    rejected = _base_row(year, month)
    rejected.update(
        {
            "tpep_pickup_datetime": datetime(year, month, 2, 9, 0),
            "tpep_dropoff_datetime": datetime(year, month, 2, 9, 20),
            "fare_amount": -5.0,
            "total_amount": -5.0,
        }
    )
    return [valid, duplicate_warning, rejected]


def _base_row(year: int, month: int) -> dict[str, object]:
    return {
        "VendorID": 1,
        "tpep_pickup_datetime": datetime(year, month, 1, 8, 0),
        "tpep_dropoff_datetime": datetime(year, month, 1, 8, 30),
        "passenger_count": 1,
        "trip_distance": 3.0,
        "RatecodeID": 1,
        "store_and_fwd_flag": "N",
        "PULocationID": 1,
        "DOLocationID": 132,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a tiny local demo fixture.")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=1)
    parser.add_argument("--service", choices=("yellow",), default="yellow")
    parser.add_argument("--sample-rows", type=int, default=DEFAULT_SAMPLE_ROWS)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    result = create_demo_fixture(
        data_dir=get_data_dir(),
        year=arguments.year,
        month=arguments.month,
        service=arguments.service,
        sample_rows=arguments.sample_rows,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
