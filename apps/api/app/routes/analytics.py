from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query
from fastapi.responses import StreamingResponse

from apps.api.app.repositories.analytics import AnalyticsRepository
from apps.api.app.repositories.quality import QualityReportRepository
from apps.api.app.schemas.responses import (
    AnomalousTrip,
    DailyMetric,
    HealthResponse,
    HourlyDemandMetric,
    MetadataResponse,
    OverviewMetrics,
    PaginatedResponse,
    QualitySummaryResponse,
    RevenueMetric,
    RouteMetric,
    ZoneMetric,
    ZoneSummary,
)
from apps.api.app.services.analytics import AnalyticsService
from urban_mobility.config import get_data_dir, get_duckdb_path

router = APIRouter()

StartDate = Annotated[date | None, Query(description="Inclusive pickup start date.")]
EndDate = Annotated[date | None, Query(description="Inclusive pickup end date.")]
ZoneFilter = Annotated[int | None, Query(ge=1, description="Pickup or dropoff zone ID.")]
Limit = Annotated[int, Query(ge=1, le=500)]
Offset = Annotated[int, Query(ge=0)]
SortOrder = Literal["asc", "desc"]


def get_analytics_service() -> AnalyticsService:
    repository = AnalyticsRepository(get_duckdb_path())
    quality_reports = QualityReportRepository(get_data_dir())
    return AnalyticsService(repository, quality_reports)


Service = Annotated[AnalyticsService, Depends(get_analytics_service)]


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(service: Service) -> dict:
    return service.health()


@router.get("/metadata", response_model=MetadataResponse, tags=["system"])
def metadata(service: Service) -> dict:
    return service.metadata()


@router.get("/quality/summary", response_model=QualitySummaryResponse, tags=["quality"])
def quality_summary(service: Service) -> dict:
    return service.quality_summary()


@router.get("/metrics/overview", response_model=OverviewMetrics, tags=["metrics"])
def overview(
    service: Service,
    start_date: StartDate = None,
    end_date: EndDate = None,
    zone_id: ZoneFilter = None,
) -> dict:
    return service.overview(start_date, end_date, zone_id)


@router.get(
    "/metrics/daily",
    response_model=PaginatedResponse[DailyMetric],
    tags=["metrics"],
)
def daily_metrics(
    service: Service,
    start_date: StartDate = None,
    end_date: EndDate = None,
    limit: Limit = 100,
    offset: Offset = 0,
    sort_by: Literal[
        "pickup_date",
        "trip_count",
        "total_revenue",
        "average_duration_minutes",
    ] = "pickup_date",
    sort_order: SortOrder = "asc",
) -> dict:
    page = service.daily_metrics(
        start_date,
        end_date,
        limit,
        offset,
        sort_by,
        sort_order,
    )
    return {"items": page.items, "total": page.total, "limit": limit, "offset": offset}


@router.get(
    "/metrics/hourly-demand",
    response_model=PaginatedResponse[HourlyDemandMetric],
    tags=["metrics"],
)
def hourly_demand(
    service: Service,
    start_date: StartDate = None,
    end_date: EndDate = None,
    limit: Limit = 100,
    offset: Offset = 0,
    sort_by: Literal[
        "pickup_date",
        "pickup_hour",
        "trip_count",
        "total_revenue",
    ] = "pickup_date",
    sort_order: SortOrder = "asc",
) -> dict:
    page = service.hourly_demand(
        start_date,
        end_date,
        limit,
        offset,
        sort_by,
        sort_order,
    )
    return {"items": page.items, "total": page.total, "limit": limit, "offset": offset}


@router.get(
    "/metrics/revenue",
    response_model=PaginatedResponse[RevenueMetric],
    tags=["metrics"],
)
def revenue_metrics(
    service: Service,
    start_date: StartDate = None,
    end_date: EndDate = None,
    limit: Limit = 100,
    offset: Offset = 0,
    sort_by: Literal[
        "pickup_date",
        "trip_count",
        "total_revenue",
        "payment_type",
    ] = "pickup_date",
    sort_order: SortOrder = "asc",
) -> dict:
    page = service.revenue_metrics(
        start_date,
        end_date,
        limit,
        offset,
        sort_by,
        sort_order,
    )
    return {"items": page.items, "total": page.total, "limit": limit, "offset": offset}


@router.get("/zones", response_model=PaginatedResponse[ZoneMetric], tags=["zones"])
def zones(
    service: Service,
    limit: Limit = 100,
    offset: Offset = 0,
    sort_by: Literal[
        "zone_id",
        "zone_name",
        "pickup_trip_count",
        "total_revenue",
    ] = "zone_id",
    sort_order: SortOrder = "asc",
) -> dict:
    page = service.zones(limit, offset, sort_by, sort_order)
    return {"items": page.items, "total": page.total, "limit": limit, "offset": offset}


@router.get("/zones/{zone_id}/summary", response_model=ZoneSummary, tags=["zones"])
def zone_summary(
    service: Service,
    zone_id: Annotated[int, Path(ge=1)],
    start_date: StartDate = None,
    end_date: EndDate = None,
) -> dict:
    return service.zone_summary(zone_id, start_date, end_date)


@router.get(
    "/routes/top",
    response_model=PaginatedResponse[RouteMetric],
    tags=["routes"],
)
def top_routes(
    service: Service,
    zone_id: ZoneFilter = None,
    limit: Limit = 100,
    offset: Offset = 0,
    sort_by: Literal[
        "trip_count",
        "total_revenue",
        "average_trip_distance",
        "average_duration_minutes",
    ] = "trip_count",
    sort_order: SortOrder = "desc",
) -> dict:
    page = service.top_routes(zone_id, limit, offset, sort_by, sort_order)
    return {"items": page.items, "total": page.total, "limit": limit, "offset": offset}


@router.get(
    "/anomalies",
    response_model=PaginatedResponse[AnomalousTrip],
    tags=["anomalies"],
)
def anomalies(
    service: Service,
    start_date: StartDate = None,
    end_date: EndDate = None,
    zone_id: ZoneFilter = None,
    limit: Limit = 100,
    offset: Offset = 0,
    sort_by: Literal[
        "pickup_datetime",
        "total_amount",
        "trip_distance",
        "average_speed_mph",
    ] = "pickup_datetime",
    sort_order: SortOrder = "desc",
) -> dict:
    page = service.anomalies(
        start_date,
        end_date,
        zone_id,
        limit,
        offset,
        sort_by,
        sort_order,
    )
    return {"items": page.items, "total": page.total, "limit": limit, "offset": offset}


@router.get("/exports/daily-metrics.csv", response_class=StreamingResponse, tags=["exports"])
def daily_metrics_csv(
    service: Service,
    start_date: StartDate = None,
    end_date: EndDate = None,
) -> StreamingResponse:
    content = service.daily_csv(start_date, end_date)
    return StreamingResponse(
        iter((content,)),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=daily-metrics.csv"},
    )
