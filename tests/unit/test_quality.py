from datetime import datetime, timedelta

from urban_mobility.quality import (
    average_speed_mph,
    duration_minutes,
    revenue_per_mile,
)


def test_duration_minutes_uses_elapsed_time() -> None:
    pickup = datetime(2026, 1, 1, 12, 0)

    assert duration_minutes(pickup, pickup + timedelta(minutes=37, seconds=30)) == 37.5


def test_average_speed_handles_zero_duration() -> None:
    assert average_speed_mph(3.0, 30.0) == 6.0
    assert average_speed_mph(3.0, 0.0) is None


def test_revenue_per_mile_handles_zero_distance() -> None:
    assert revenue_per_mile(25.0, 5.0) == 5.0
    assert revenue_per_mile(25.0, 0.0) is None
