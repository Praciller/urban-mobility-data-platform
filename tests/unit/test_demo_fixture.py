from __future__ import annotations

from pathlib import Path

import pyarrow.parquet as pq

from scripts.create_demo_fixture import create_demo_fixture
from urban_mobility.download import trip_data_path, zone_lookup_path


def test_create_demo_fixture_writes_trip_sample_and_zone_lookup(tmp_path: Path) -> None:
    result = create_demo_fixture(
        data_dir=tmp_path,
        year=2026,
        month=1,
        service="yellow",
        sample_rows=1000,
    )

    trip_path = trip_data_path(tmp_path, 2026, 1, "yellow", sample=True, sample_rows=1000)
    zones = zone_lookup_path(tmp_path)

    assert result["trip_path"] == str(trip_path)
    assert result["zone_lookup_path"] == str(zones)
    assert trip_path.is_file()
    assert zones.is_file()
    table = pq.read_table(trip_path)
    assert table.num_rows == 3
    assert table["tpep_pickup_datetime"][0].as_py().year == 2026
    assert table["tpep_pickup_datetime"][0].as_py().month == 1
