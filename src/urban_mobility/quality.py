from __future__ import annotations

from datetime import datetime


def duration_minutes(pickup: datetime, dropoff: datetime) -> float:
    """Return elapsed trip time in minutes."""
    return (dropoff - pickup).total_seconds() / 60


def average_speed_mph(trip_distance: float, trip_duration_minutes: float) -> float | None:
    """Return average speed, or None when elapsed time is not positive."""
    if trip_duration_minutes <= 0:
        return None
    return trip_distance / (trip_duration_minutes / 60)


def revenue_per_mile(total_amount: float, trip_distance: float) -> float | None:
    """Return revenue per mile, or None when distance is not positive."""
    if trip_distance <= 0:
        return None
    return total_amount / trip_distance
