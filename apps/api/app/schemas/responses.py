from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class DateRange(BaseModel):
    start_date: date
    end_date: date


class HealthResponse(BaseModel):
    status: str
    duckdb_available: bool
    data_freshness: datetime | None = None
    available_marts: list[str]
    missing_marts: list[str]


class MetadataResponse(BaseModel):
    supported_services: list[str]
    service_status: dict[str, str]
    available_date_range: DateRange | None = None
    row_counts: dict[str, int]


class ValidationStatusCounts(BaseModel):
    valid: int = Field(ge=0)
    warning: int = Field(ge=0)
    rejected: int = Field(ge=0)


class QualitySummaryResponse(BaseModel):
    service: str
    year: int
    month: int = Field(ge=1, le=12)
    validated_at: datetime
    total_rows: int = Field(ge=0)
    status_counts: ValidationStatusCounts
    rule_counts: dict[str, int]
    artifact_name: str


class OverviewMetrics(BaseModel):
    total_trips: int
    total_revenue: float
    average_fare: float
    average_duration_minutes: float
    total_distance: float
    airport_trip_count: int
    warning_trip_count: int


class PaginatedResponse[ItemT](BaseModel):
    items: list[ItemT]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class DailyMetric(BaseModel):
    pickup_date: date
    trip_count: int
    passenger_count: float
    trip_distance: float
    total_revenue: float
    average_duration_minutes: float
    average_speed_mph: float | None
    airport_trip_count: int


class HourlyDemandMetric(BaseModel):
    pickup_date: date
    pickup_hour: int = Field(ge=0, le=23)
    trip_count: int
    passenger_count: float
    average_duration_minutes: float
    total_revenue: float


class RevenueMetric(BaseModel):
    pickup_date: date
    payment_type: int
    trip_count: int
    fare_revenue: float
    tip_revenue: float
    tolls_revenue: float
    total_revenue: float
    average_revenue_per_mile: float | None


class ZoneMetric(BaseModel):
    zone_id: int
    borough: str
    zone_name: str
    service_zone: str
    is_airport_zone: bool
    pickup_trip_count: int
    passenger_count: float
    total_revenue: float
    average_trip_distance: float | None


class ZoneSummary(BaseModel):
    zone_id: int
    borough: str
    zone_name: str
    service_zone: str
    is_airport_zone: bool
    pickup_trip_count: int
    dropoff_trip_count: int
    related_trip_count: int
    total_revenue: float
    average_trip_distance: float | None
    average_duration_minutes: float | None


class RouteMetric(BaseModel):
    pickup_zone_id: int
    pickup_zone_name: str
    dropoff_zone_id: int
    dropoff_zone_name: str
    trip_count: int
    average_trip_distance: float
    average_duration_minutes: float
    total_revenue: float


class AnomalousTrip(BaseModel):
    trip_id: str
    pickup_datetime: datetime
    dropoff_datetime: datetime
    pickup_zone_id: int
    pickup_zone_name: str
    dropoff_zone_id: int
    dropoff_zone_name: str
    passenger_count: float | None
    trip_distance: float
    fare_amount: float
    total_amount: float
    duration_minutes: float
    average_speed_mph: float | None
    revenue_per_mile: float | None
    is_airport_trip: bool
    quality_status: str
    quality_reasons: str
