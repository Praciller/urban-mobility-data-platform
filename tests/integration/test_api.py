from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from apps.api.app.main import app


def create_api_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(path)) as connection:
        connection.execute(
            """
            create table dim_zone as
            select *
            from (
                values
                    (1, 'Manhattan', 'Alpha', 'Yellow Zone', false),
                    (2, 'Queens', 'Beta', 'Boro Zone', false),
                    (132, 'Queens', 'JFK Airport', 'Airports', true)
            ) as zones(zone_id, borough, zone_name, service_zone, is_airport_zone)
            """
        )
        connection.execute(
            """
            create table fct_trips as
            select *
            from (
                values
                    (
                        'trip-1', 'yellow', timestamp '2026-01-01 08:00:00',
                        timestamp '2026-01-01 08:30:00', date '2026-01-01', 8, 1, 2,
                        1.0, 3.0, 18.0, 3.0, 0.0, 23.5, 1, 1, 30.0, 6.0, 7.833333,
                        false, 'valid', '', 'fixture.parquet', timestamp '2026-01-03 10:00:00'
                    ),
                    (
                        'trip-2', 'yellow', timestamp '2026-01-01 09:00:00',
                        timestamp '2026-01-01 10:00:00', date '2026-01-01', 9, 1, 132,
                        2.0, 10.0, 50.0, 8.0, 0.0, 60.0, 1, 2, 60.0, 10.0, 6.0,
                        true, 'warning', 'duplicate_record', 'fixture.parquet',
                        timestamp '2026-01-03 10:00:00'
                    ),
                    (
                        'trip-3', 'yellow', timestamp '2026-01-02 08:00:00',
                        timestamp '2026-01-02 08:20:00', date '2026-01-02', 8, 2, 1,
                        1.0, 2.0, 12.0, 2.0, 0.0, 15.0, 2, 1, 20.0, 6.0, 7.5,
                        false, 'valid', '', 'fixture.parquet', timestamp '2026-01-03 10:00:00'
                    )
            ) as trips(
                trip_id, service, pickup_datetime, dropoff_datetime, pickup_date,
                pickup_hour, pickup_zone_id, dropoff_zone_id, passenger_count,
                trip_distance, fare_amount, tip_amount, tolls_amount, total_amount,
                payment_type, rate_code_id, duration_minutes, average_speed_mph,
                revenue_per_mile, is_airport_trip, quality_status, quality_reasons,
                source_file, ingested_at
            )
            """
        )
        connection.execute(
            """
            create table mart_daily_trip_metrics as
            select *
            from (
                values
                    (date '2026-01-01', 2, 3.0, 13.0, 83.5, 45.0, 8.0, 1),
                    (date '2026-01-02', 1, 1.0, 2.0, 15.0, 20.0, 6.0, 0)
            ) as daily(
                pickup_date, trip_count, passenger_count, trip_distance, total_revenue,
                average_duration_minutes, average_speed_mph, airport_trip_count
            )
            """
        )
        connection.execute(
            """
            create table mart_hourly_demand as
            select *
            from (
                values
                    (date '2026-01-01', 8, 1, 1.0, 30.0, 23.5),
                    (date '2026-01-01', 9, 1, 2.0, 60.0, 60.0),
                    (date '2026-01-02', 8, 1, 1.0, 20.0, 15.0)
            ) as hourly(
                pickup_date, pickup_hour, trip_count, passenger_count,
                average_duration_minutes, total_revenue
            )
            """
        )
        connection.execute(
            """
            create table mart_zone_demand as
            select *
            from (
                values
                    (1, 2, 3.0, 83.5, 6.5),
                    (2, 1, 1.0, 15.0, 2.0)
            ) as demand(
                zone_id, pickup_trip_count, passenger_count, total_revenue,
                average_trip_distance
            )
            """
        )
        connection.execute(
            """
            create table mart_route_metrics as
            select *
            from (
                values
                    (1, 2, 1, 3.0, 30.0, 23.5),
                    (1, 132, 1, 10.0, 60.0, 60.0),
                    (2, 1, 1, 2.0, 20.0, 15.0)
            ) as routes(
                pickup_zone_id, dropoff_zone_id, trip_count, average_trip_distance,
                average_duration_minutes, total_revenue
            )
            """
        )
        connection.execute(
            """
            create table mart_revenue_metrics as
            select *
            from (
                values
                    (date '2026-01-01', 1, 2, 68.0, 11.0, 0.0, 83.5, 6.9166665),
                    (date '2026-01-02', 2, 1, 12.0, 2.0, 0.0, 15.0, 7.5)
            ) as revenue(
                pickup_date, payment_type, trip_count, fare_revenue, tip_revenue,
                tolls_revenue, total_revenue, average_revenue_per_mile
            )
            """
        )
        connection.execute(
            """
            create table mart_anomalous_trips as
            select *
            from fct_trips
            where quality_status = 'warning'
            """
        )


@pytest.fixture
def api_client(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Iterator[TestClient]:
    database = tmp_path / "external-data" / "processed" / "api.duckdb"
    create_api_database(database)
    quality_dir = database.parents[1] / "reports" / "data_quality"
    quality_dir.mkdir(parents=True)
    (quality_dir / "validation_2026_01.json").write_text(
        json.dumps(
            {
                "service": "yellow",
                "year": 2026,
                "month": 1,
                "validated_at": "2026-01-03T10:00:00Z",
                "total_rows": 4,
                "status_counts": {"valid": 2, "warning": 1, "rejected": 1},
                "rule_counts": {"duplicate_record": 1, "negative_fare_amount": 1},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("DATA_DIR", str(database.parents[1]))
    monkeypatch.setenv("DUCKDB_PATH", str(database))
    with TestClient(app) as client:
        yield client


def test_health_reports_database_and_freshness(api_client: TestClient) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["duckdb_available"] is True
    assert "duckdb_path" not in payload
    assert payload["data_freshness"] == "2026-01-03T10:00:00"
    assert "mart_daily_trip_metrics" in payload["available_marts"]
    assert payload["missing_marts"] == []


def test_metadata_reports_service_dates_and_counts(api_client: TestClient) -> None:
    response = api_client.get("/metadata")

    assert response.status_code == 200
    payload = response.json()
    assert payload["supported_services"] == ["yellow"]
    assert payload["service_status"] == {"yellow": "available"}
    assert payload["available_date_range"] == {
        "start_date": "2026-01-01",
        "end_date": "2026-01-02",
    }
    assert payload["row_counts"]["fct_trips"] == 3
    assert payload["row_counts"]["mart_anomalous_trips"] == 1


def test_quality_summary_exposes_bounded_validation_evidence(api_client: TestClient) -> None:
    response = api_client.get("/quality/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status_counts"] == {"valid": 2, "warning": 1, "rejected": 1}
    assert payload["rule_counts"]["negative_fare_amount"] == 1
    assert payload["artifact_name"] == "validation_2026_01.json"
    assert "external-data" not in response.text


def test_overview_supports_date_and_zone_filters(api_client: TestClient) -> None:
    response = api_client.get(
        "/metrics/overview",
        params={"start_date": "2026-01-01", "end_date": "2026-01-01", "zone_id": 1},
    )

    assert response.status_code == 200
    assert response.json() == {
        "total_trips": 2,
        "total_revenue": 83.5,
        "average_fare": 34.0,
        "average_duration_minutes": 45.0,
        "total_distance": 13.0,
        "airport_trip_count": 1,
        "warning_trip_count": 1,
    }

    missing = api_client.get("/metrics/overview", params={"zone_id": 999})
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Zone 999 was not found"


def test_daily_metrics_are_paginated_and_sorted(api_client: TestClient) -> None:
    response = api_client.get(
        "/metrics/daily",
        params={
            "limit": 1,
            "offset": 1,
            "sort_by": "pickup_date",
            "sort_order": "asc",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["limit"] == 1
    assert payload["offset"] == 1
    assert payload["items"][0]["pickup_date"] == "2026-01-02"


def test_hourly_demand_returns_bounded_results(api_client: TestClient) -> None:
    response = api_client.get(
        "/metrics/hourly-demand",
        params={"start_date": "2026-01-01", "end_date": "2026-01-01", "limit": 10},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert [item["pickup_hour"] for item in payload["items"]] == [8, 9]


def test_revenue_metrics_support_date_filters(api_client: TestClient) -> None:
    response = api_client.get(
        "/metrics/revenue",
        params={"start_date": "2026-01-02", "end_date": "2026-01-02"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["total_revenue"] == 15.0


def test_zones_support_limit_and_sorting(api_client: TestClient) -> None:
    response = api_client.get(
        "/zones",
        params={"limit": 2, "sort_by": "pickup_trip_count", "sort_order": "desc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert [item["zone_id"] for item in payload["items"]] == [1, 2]


def test_zone_summary_and_unknown_zone(api_client: TestClient) -> None:
    response = api_client.get("/zones/1/summary")

    assert response.status_code == 200
    payload = response.json()
    assert payload["zone_name"] == "Alpha"
    assert payload["pickup_trip_count"] == 2
    assert payload["dropoff_trip_count"] == 1

    missing = api_client.get("/zones/999/summary")
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Zone 999 was not found"


def test_top_routes_support_zone_filter(api_client: TestClient) -> None:
    response = api_client.get(
        "/routes/top",
        params={"zone_id": 132, "sort_by": "total_revenue", "sort_order": "desc"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["pickup_zone_name"] == "Alpha"
    assert payload["items"][0]["dropoff_zone_name"] == "JFK Airport"


def test_anomalies_are_paginated_and_explainable(api_client: TestClient) -> None:
    response = api_client.get("/anomalies", params={"limit": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["trip_id"] == "trip-2"
    assert payload["items"][0]["quality_reasons"] == "duplicate_record"


def test_daily_csv_export(api_client: TestClient) -> None:
    response = api_client.get(
        "/exports/daily-metrics.csv",
        params={"start_date": "2026-01-01", "end_date": "2026-01-01"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment; filename=daily-metrics.csv" in response.headers["content-disposition"]
    lines = response.text.strip().splitlines()
    assert lines[0].startswith("pickup_date,trip_count")
    assert lines[1].startswith("2026-01-01,2")


def test_invalid_dates_return_clear_validation_errors(api_client: TestClient) -> None:
    invalid_format = api_client.get("/metrics/daily", params={"start_date": "not-a-date"})
    assert invalid_format.status_code == 422

    invalid_order = api_client.get(
        "/metrics/daily",
        params={"start_date": "2026-01-02", "end_date": "2026-01-01"},
    )
    assert invalid_order.status_code == 422
    assert invalid_order.json()["detail"] == "start_date must be on or before end_date"


def test_query_parameter_bounds_are_enforced(api_client: TestClient) -> None:
    response = api_client.get("/zones", params={"limit": 501})

    assert response.status_code == 422


def test_cors_is_limited_to_local_dashboard_origins(api_client: TestClient) -> None:
    allowed = api_client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    rejected = api_client.options(
        "/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in rejected.headers


def test_missing_database_has_degraded_health_and_503(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.duckdb"
    monkeypatch.setenv("DUCKDB_PATH", str(missing))

    with TestClient(app) as client:
        health = client.get("/health")
        overview = client.get("/metrics/overview")

    assert health.status_code == 200
    assert health.json()["status"] == "unavailable"
    assert health.json()["duckdb_available"] is False
    assert overview.status_code == 503
    assert overview.json()["detail"] == "DuckDB database is unavailable"
    assert str(missing) not in overview.text


def test_missing_mart_returns_503(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    database = tmp_path / "incomplete.duckdb"
    with duckdb.connect(str(database)) as connection:
        connection.execute("create table dim_zone(zone_id integer)")
    monkeypatch.setenv("DUCKDB_PATH", str(database))

    with TestClient(app) as client:
        response = client.get("/metrics/daily")

    assert response.status_code == 503
    assert response.json()["detail"] == (
        "Required DuckDB relation is missing: mart_daily_trip_metrics"
    )
