from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb

from apps.api.app.core.errors import (
    DataUnavailableError,
    EmptyResultError,
    ResourceNotFoundError,
)

MART_RELATIONS = (
    "mart_daily_trip_metrics",
    "mart_hourly_demand",
    "mart_zone_demand",
    "mart_route_metrics",
    "mart_revenue_metrics",
    "mart_anomalous_trips",
)
KEY_RELATIONS = ("fct_trips", "dim_zone", *MART_RELATIONS)


@dataclass(frozen=True)
class HealthSnapshot:
    duckdb_available: bool
    available_relations: frozenset[str]
    data_freshness: datetime | None


@dataclass(frozen=True)
class PageResult:
    items: list[dict[str, Any]]
    total: int


class AnalyticsRepository:
    def __init__(self, duckdb_path: Path) -> None:
        self.duckdb_path = duckdb_path.expanduser().resolve()

    def health_snapshot(self) -> HealthSnapshot:
        if not self.duckdb_path.is_file():
            return HealthSnapshot(False, frozenset(), None)

        try:
            with self._connect() as connection:
                relations = self._relation_names(connection)
                freshness = None
                if "fct_trips" in relations:
                    freshness = connection.execute(
                        "select max(ingested_at) from fct_trips"
                    ).fetchone()[0]
                return HealthSnapshot(True, relations, freshness)
        except DataUnavailableError:
            return HealthSnapshot(False, frozenset(), None)

    def metadata(self) -> dict[str, Any]:
        with self._connect() as connection:
            self._require_relations(connection, KEY_RELATIONS)
            row_counts = {
                relation: int(connection.execute(f"select count(*) from {relation}").fetchone()[0])
                for relation in KEY_RELATIONS
            }
            start_date, end_date = connection.execute(
                "select min(pickup_date), max(pickup_date) from fct_trips"
            ).fetchone()
            yellow_count = connection.execute(
                "select count(*) from fct_trips where service = ?",
                ["yellow"],
            ).fetchone()[0]

        return {
            "supported_services": ["yellow"],
            "service_status": {"yellow": "available" if yellow_count else "empty"},
            "available_date_range": (
                {"start_date": start_date, "end_date": end_date}
                if start_date is not None and end_date is not None
                else None
            ),
            "row_counts": row_counts,
        }

    def overview(
        self,
        start_date: date | None,
        end_date: date | None,
        zone_id: int | None,
    ) -> dict[str, Any]:
        conditions, parameters = _date_conditions("pickup_date", start_date, end_date)
        if zone_id is not None:
            conditions.append("(pickup_zone_id = ? or dropoff_zone_id = ?)")
            parameters.extend((zone_id, zone_id))
        where_clause = _where_clause(conditions)

        with self._connect() as connection:
            required_relations = (
                ("fct_trips", "dim_zone") if zone_id is not None else ("fct_trips",)
            )
            self._require_relations(connection, required_relations)
            if zone_id is not None:
                self._zone(connection, zone_id)
            row = self._fetch_one(
                connection,
                f"""
                select
                    count(*)::bigint as total_trips,
                    coalesce(sum(total_amount), 0)::double as total_revenue,
                    coalesce(avg(fare_amount), 0)::double as average_fare,
                    coalesce(avg(duration_minutes), 0)::double
                        as average_duration_minutes,
                    coalesce(sum(trip_distance), 0)::double as total_distance,
                    count(*) filter (where is_airport_trip)::bigint as airport_trip_count,
                    count(*) filter (where quality_status = 'warning')::bigint
                        as warning_trip_count
                from fct_trips
                {where_clause}
                """,
                parameters,
            )
        if row["total_trips"] == 0:
            raise EmptyResultError("No overview metrics found for the supplied filters")
        return row

    def daily_metrics(
        self,
        start_date: date | None,
        end_date: date | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        order_column = _sort_column(
            sort_by,
            {
                "pickup_date": "pickup_date",
                "trip_count": "trip_count",
                "total_revenue": "total_revenue",
                "average_duration_minutes": "average_duration_minutes",
            },
        )
        conditions, parameters = _date_conditions("pickup_date", start_date, end_date)
        return self._paged_query(
            relation="mart_daily_trip_metrics",
            select_sql="""
                pickup_date,
                trip_count::bigint as trip_count,
                passenger_count::double as passenger_count,
                trip_distance::double as trip_distance,
                total_revenue::double as total_revenue,
                average_duration_minutes::double as average_duration_minutes,
                average_speed_mph::double as average_speed_mph,
                airport_trip_count::bigint as airport_trip_count
            """,
            conditions=conditions,
            parameters=parameters,
            limit=limit,
            offset=offset,
            order_sql=f"{order_column} {_sort_direction(sort_order)}, pickup_date asc",
            empty_message="No daily metrics found for the supplied filters",
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
        order_column = _sort_column(
            sort_by,
            {
                "pickup_date": "pickup_date",
                "pickup_hour": "pickup_hour",
                "trip_count": "trip_count",
                "total_revenue": "total_revenue",
            },
        )
        conditions, parameters = _date_conditions("pickup_date", start_date, end_date)
        return self._paged_query(
            relation="mart_hourly_demand",
            select_sql="""
                pickup_date,
                pickup_hour::integer as pickup_hour,
                trip_count::bigint as trip_count,
                passenger_count::double as passenger_count,
                average_duration_minutes::double as average_duration_minutes,
                total_revenue::double as total_revenue
            """,
            conditions=conditions,
            parameters=parameters,
            limit=limit,
            offset=offset,
            order_sql=(
                f"{order_column} {_sort_direction(sort_order)}, pickup_date asc, pickup_hour asc"
            ),
            empty_message="No hourly demand metrics found for the supplied filters",
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
        order_column = _sort_column(
            sort_by,
            {
                "pickup_date": "pickup_date",
                "trip_count": "trip_count",
                "total_revenue": "total_revenue",
                "payment_type": "payment_type",
            },
        )
        conditions, parameters = _date_conditions("pickup_date", start_date, end_date)
        return self._paged_query(
            relation="mart_revenue_metrics",
            select_sql="""
                pickup_date,
                payment_type::integer as payment_type,
                trip_count::bigint as trip_count,
                fare_revenue::double as fare_revenue,
                tip_revenue::double as tip_revenue,
                tolls_revenue::double as tolls_revenue,
                total_revenue::double as total_revenue,
                average_revenue_per_mile::double as average_revenue_per_mile
            """,
            conditions=conditions,
            parameters=parameters,
            limit=limit,
            offset=offset,
            order_sql=(
                f"{order_column} {_sort_direction(sort_order)}, pickup_date asc, payment_type asc"
            ),
            empty_message="No revenue metrics found for the supplied filters",
        )

    def zones(
        self,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        order_column = _sort_column(
            sort_by,
            {
                "zone_id": "zones.zone_id",
                "zone_name": "zones.zone_name",
                "pickup_trip_count": "pickup_trip_count",
                "total_revenue": "total_revenue",
            },
        )
        with self._connect() as connection:
            self._require_relations(connection, ("dim_zone", "mart_zone_demand"))
            total = int(connection.execute("select count(*) from dim_zone").fetchone()[0])
            if total == 0:
                raise EmptyResultError("No taxi zones are available")
            items = self._fetch_all(
                connection,
                f"""
                select
                    zones.zone_id::integer as zone_id,
                    zones.borough,
                    zones.zone_name,
                    zones.service_zone,
                    zones.is_airport_zone,
                    coalesce(demand.pickup_trip_count, 0)::bigint as pickup_trip_count,
                    coalesce(demand.passenger_count, 0)::double as passenger_count,
                    coalesce(demand.total_revenue, 0)::double as total_revenue,
                    demand.average_trip_distance::double as average_trip_distance
                from dim_zone as zones
                left join mart_zone_demand as demand using (zone_id)
                order by {order_column} {_sort_direction(sort_order)}, zones.zone_id asc
                limit ? offset ?
                """,
                [limit, offset],
            )
        return PageResult(items=items, total=total)

    def zone_summary(
        self,
        zone_id: int,
        start_date: date | None,
        end_date: date | None,
    ) -> dict[str, Any]:
        conditions, parameters = _date_conditions("pickup_date", start_date, end_date)
        conditions.append("(pickup_zone_id = ? or dropoff_zone_id = ?)")
        parameters.extend((zone_id, zone_id))

        with self._connect() as connection:
            self._require_relations(connection, ("dim_zone", "fct_trips"))
            zone = self._zone(connection, zone_id)
            summary = self._fetch_one(
                connection,
                f"""
                select
                    count(*) filter (where pickup_zone_id = ?)::bigint
                        as pickup_trip_count,
                    count(*) filter (where dropoff_zone_id = ?)::bigint
                        as dropoff_trip_count,
                    count(*)::bigint as related_trip_count,
                    coalesce(sum(total_amount), 0)::double as total_revenue,
                    avg(trip_distance)::double as average_trip_distance,
                    avg(duration_minutes)::double as average_duration_minutes
                from fct_trips
                {_where_clause(conditions)}
                """,
                [zone_id, zone_id, *parameters],
            )
        return {**zone, **summary}

    def top_routes(
        self,
        zone_id: int | None,
        limit: int,
        offset: int,
        sort_by: str,
        sort_order: str,
    ) -> PageResult:
        order_column = _sort_column(
            sort_by,
            {
                "trip_count": "routes.trip_count",
                "total_revenue": "routes.total_revenue",
                "average_trip_distance": "routes.average_trip_distance",
                "average_duration_minutes": "routes.average_duration_minutes",
            },
        )
        conditions: list[str] = []
        parameters: list[Any] = []
        if zone_id is not None:
            conditions.append("(routes.pickup_zone_id = ? or routes.dropoff_zone_id = ?)")
            parameters.extend((zone_id, zone_id))
        where_clause = _where_clause(conditions)

        with self._connect() as connection:
            self._require_relations(connection, ("mart_route_metrics", "dim_zone"))
            if zone_id is not None:
                self._zone(connection, zone_id)
            total = int(
                connection.execute(
                    f"select count(*) from mart_route_metrics as routes {where_clause}",
                    parameters,
                ).fetchone()[0]
            )
            if total == 0:
                raise EmptyResultError("No route metrics found for the supplied filters")
            items = self._fetch_all(
                connection,
                f"""
                select
                    routes.pickup_zone_id::integer as pickup_zone_id,
                    pickup.zone_name as pickup_zone_name,
                    routes.dropoff_zone_id::integer as dropoff_zone_id,
                    dropoff.zone_name as dropoff_zone_name,
                    routes.trip_count::bigint as trip_count,
                    routes.average_trip_distance::double as average_trip_distance,
                    routes.average_duration_minutes::double as average_duration_minutes,
                    routes.total_revenue::double as total_revenue
                from mart_route_metrics as routes
                join dim_zone as pickup on pickup.zone_id = routes.pickup_zone_id
                join dim_zone as dropoff on dropoff.zone_id = routes.dropoff_zone_id
                {where_clause}
                order by {order_column} {_sort_direction(sort_order)},
                         routes.pickup_zone_id asc,
                         routes.dropoff_zone_id asc
                limit ? offset ?
                """,
                [*parameters, limit, offset],
            )
        return PageResult(items=items, total=total)

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
        order_column = _sort_column(
            sort_by,
            {
                "pickup_datetime": "trips.pickup_datetime",
                "total_amount": "trips.total_amount",
                "trip_distance": "trips.trip_distance",
                "average_speed_mph": "trips.average_speed_mph",
            },
        )
        conditions, parameters = _date_conditions(
            "trips.pickup_date",
            start_date,
            end_date,
        )
        if zone_id is not None:
            conditions.append("(trips.pickup_zone_id = ? or trips.dropoff_zone_id = ?)")
            parameters.extend((zone_id, zone_id))
        where_clause = _where_clause(conditions)

        with self._connect() as connection:
            self._require_relations(connection, ("mart_anomalous_trips", "dim_zone"))
            if zone_id is not None:
                self._zone(connection, zone_id)
            total = int(
                connection.execute(
                    f"select count(*) from mart_anomalous_trips as trips {where_clause}",
                    parameters,
                ).fetchone()[0]
            )
            if total == 0:
                raise EmptyResultError("No anomalous trips found for the supplied filters")
            items = self._fetch_all(
                connection,
                f"""
                select
                    trips.trip_id,
                    trips.pickup_datetime,
                    trips.dropoff_datetime,
                    trips.pickup_zone_id::integer as pickup_zone_id,
                    pickup.zone_name as pickup_zone_name,
                    trips.dropoff_zone_id::integer as dropoff_zone_id,
                    dropoff.zone_name as dropoff_zone_name,
                    trips.passenger_count::double as passenger_count,
                    trips.trip_distance::double as trip_distance,
                    trips.fare_amount::double as fare_amount,
                    trips.total_amount::double as total_amount,
                    trips.duration_minutes::double as duration_minutes,
                    trips.average_speed_mph::double as average_speed_mph,
                    trips.revenue_per_mile::double as revenue_per_mile,
                    trips.is_airport_trip,
                    trips.quality_status,
                    trips.quality_reasons
                from mart_anomalous_trips as trips
                join dim_zone as pickup on pickup.zone_id = trips.pickup_zone_id
                join dim_zone as dropoff on dropoff.zone_id = trips.dropoff_zone_id
                {where_clause}
                order by {order_column} {_sort_direction(sort_order)}, trips.trip_id asc
                limit ? offset ?
                """,
                [*parameters, limit, offset],
            )
        return PageResult(items=items, total=total)

    def daily_export(
        self,
        start_date: date | None,
        end_date: date | None,
    ) -> list[dict[str, Any]]:
        page = self.daily_metrics(
            start_date=start_date,
            end_date=end_date,
            limit=10_000,
            offset=0,
            sort_by="pickup_date",
            sort_order="asc",
        )
        return page.items

    def _paged_query(
        self,
        *,
        relation: str,
        select_sql: str,
        conditions: list[str],
        parameters: list[Any],
        limit: int,
        offset: int,
        order_sql: str,
        empty_message: str,
    ) -> PageResult:
        where_clause = _where_clause(conditions)
        with self._connect() as connection:
            self._require_relations(connection, (relation,))
            total = int(
                connection.execute(
                    f"select count(*) from {relation} {where_clause}",
                    parameters,
                ).fetchone()[0]
            )
            if total == 0:
                raise EmptyResultError(empty_message)
            items = self._fetch_all(
                connection,
                f"""
                select {select_sql}
                from {relation}
                {where_clause}
                order by {order_sql}
                limit ? offset ?
                """,
                [*parameters, limit, offset],
            )
        return PageResult(items=items, total=total)

    def _zone(
        self,
        connection: duckdb.DuckDBPyConnection,
        zone_id: int,
    ) -> dict[str, Any]:
        rows = self._fetch_all(
            connection,
            """
            select
                zone_id::integer as zone_id,
                borough,
                zone_name,
                service_zone,
                is_airport_zone
            from dim_zone
            where zone_id = ?
            """,
            [zone_id],
        )
        if not rows:
            raise ResourceNotFoundError(f"Zone {zone_id} was not found")
        return rows[0]

    @contextmanager
    def _connect(self) -> Iterator[duckdb.DuckDBPyConnection]:
        if not self.duckdb_path.is_file():
            raise DataUnavailableError(f"DuckDB database does not exist: {self.duckdb_path}")
        try:
            connection = duckdb.connect(str(self.duckdb_path), read_only=True)
        except duckdb.Error as error:
            raise DataUnavailableError(
                f"DuckDB database is unavailable: {self.duckdb_path}"
            ) from error
        try:
            yield connection
        except duckdb.Error as error:
            raise DataUnavailableError(
                "DuckDB query failed against the configured database"
            ) from error
        finally:
            connection.close()

    def _require_relations(
        self,
        connection: duckdb.DuckDBPyConnection,
        relations: tuple[str, ...],
    ) -> None:
        available = self._relation_names(connection)
        for relation in relations:
            if relation not in available:
                raise DataUnavailableError(f"Required DuckDB relation is missing: {relation}")

    @staticmethod
    def _relation_names(connection: duckdb.DuckDBPyConnection) -> frozenset[str]:
        rows = connection.execute(
            """
            select table_name
            from information_schema.tables
            where table_schema = 'main'
            """
        ).fetchall()
        return frozenset(str(row[0]) for row in rows)

    @staticmethod
    def _fetch_all(
        connection: duckdb.DuckDBPyConnection,
        sql: str,
        parameters: list[Any],
    ) -> list[dict[str, Any]]:
        cursor = connection.execute(sql, parameters)
        columns = [item[0] for item in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]

    def _fetch_one(
        self,
        connection: duckdb.DuckDBPyConnection,
        sql: str,
        parameters: list[Any],
    ) -> dict[str, Any]:
        rows = self._fetch_all(connection, sql, parameters)
        if not rows:
            raise EmptyResultError("The query returned no result")
        return rows[0]


def _date_conditions(
    column: str,
    start_date: date | None,
    end_date: date | None,
) -> tuple[list[str], list[Any]]:
    conditions: list[str] = []
    parameters: list[Any] = []
    if start_date is not None:
        conditions.append(f"{column} >= ?")
        parameters.append(start_date)
    if end_date is not None:
        conditions.append(f"{column} <= ?")
        parameters.append(end_date)
    return conditions, parameters


def _where_clause(conditions: list[str]) -> str:
    if not conditions:
        return ""
    return "where " + " and ".join(conditions)


def _sort_column(sort_by: str, allowed: dict[str, str]) -> str:
    try:
        return allowed[sort_by]
    except KeyError as error:
        raise ValueError(f"Unsupported sort field: {sort_by}") from error


def _sort_direction(sort_order: str) -> str:
    normalized = sort_order.lower()
    if normalized not in {"asc", "desc"}:
        raise ValueError(f"Unsupported sort order: {sort_order}")
    return normalized
