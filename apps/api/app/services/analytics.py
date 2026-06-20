from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from apps.api.app.core.errors import InvalidDateRangeError
from apps.api.app.repositories.analytics import (
    KEY_RELATIONS,
    MART_RELATIONS,
    AnalyticsRepository,
    PageResult,
)
from apps.api.app.repositories.quality import QualityReportRepository


class AnalyticsService:
    def __init__(
        self,
        repository: AnalyticsRepository,
        quality_reports: QualityReportRepository,
    ) -> None:
        self.repository = repository
        self.quality_reports = quality_reports

    def health(self) -> dict[str, Any]:
        snapshot = self.repository.health_snapshot()
        available_marts = sorted(set(MART_RELATIONS) & snapshot.available_relations)
        missing_marts = sorted(set(MART_RELATIONS) - snapshot.available_relations)
        all_relations_available = set(KEY_RELATIONS).issubset(snapshot.available_relations)
        if not snapshot.duckdb_available:
            status = "unavailable"
        elif not all_relations_available:
            status = "degraded"
        else:
            status = "ok"
        return {
            "status": status,
            "duckdb_available": snapshot.duckdb_available,
            "data_freshness": snapshot.data_freshness,
            "available_marts": available_marts,
            "missing_marts": missing_marts,
        }

    def metadata(self) -> dict[str, Any]:
        return self.repository.metadata()

    def quality_summary(self) -> dict[str, Any]:
        return self.quality_reports.latest_summary()

    def overview(
        self,
        start_date: date | None,
        end_date: date | None,
        zone_id: int | None,
    ) -> dict[str, Any]:
        self.validate_date_range(start_date, end_date)
        return self.repository.overview(start_date, end_date, zone_id)

    def daily_metrics(
        self,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        self.validate_date_range(start_date, end_date)
        return self.repository.daily_metrics(
            start_date,
            end_date,
            limit,
            offset,
            sort_by,
            sort_order,
        )

    def hourly_demand(
        self,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        self.validate_date_range(start_date, end_date)
        return self.repository.hourly_demand(
            start_date,
            end_date,
            limit,
            offset,
            sort_by,
            sort_order,
        )

    def revenue_metrics(
        self,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        self.validate_date_range(start_date, end_date)
        return self.repository.revenue_metrics(
            start_date,
            end_date,
            limit,
            offset,
            sort_by,
            sort_order,
        )

    def zone_summary(
        self,
        zone_id: int,
        start_date: date | None,
        end_date: date | None,
    ) -> dict[str, Any]:
        self.validate_date_range(start_date, end_date)
        return self.repository.zone_summary(zone_id, start_date, end_date)

    def zones(
        self,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        return self.repository.zones(limit, offset, sort_by, sort_order)

    def top_routes(
        self,
        zone_id: int | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        return self.repository.top_routes(zone_id, limit, offset, sort_by, sort_order)

    def anomalies(
        self,
        start_date: date | None,
        end_date: date | None,
        zone_id: int | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        self.validate_date_range(start_date, end_date)
        return self.repository.anomalies(
            start_date,
            end_date,
            zone_id,
            limit,
            offset,
            sort_by,
            sort_order,
        )

    def daily_csv(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> str:
        self.validate_date_range(start_date, end_date)
        rows = self.repository.daily_export(start_date, end_date)
        output = io.StringIO(newline="")
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def validate_date_range(
        start_date: date | None,
        end_date: date | None,
    ) -> None:
        if start_date is not None and end_date is not None and start_date > end_date:
            raise InvalidDateRangeError("start_date must be on or before end_date")
