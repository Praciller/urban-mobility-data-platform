import { vi } from "vitest";

import type {
  AnomaliesResponse,
  DailyMetricsResponse,
  DashboardData,
  HealthResponse,
  HourlyDemandResponse,
  MetadataResponse,
  OverviewMetrics,
  QualitySummary,
  RevenueMetricsResponse,
  RoutesResponse,
  ZoneSummary,
  ZonesResponse,
} from "../api/types";

const health: HealthResponse = {
  status: "ok",
  duckdb_available: true,
  data_freshness: "2026-01-03T10:00:00",
  available_marts: ["mart_daily_trip_metrics", "mart_route_metrics"],
  missing_marts: [],
};

const metadata: MetadataResponse = {
  supported_services: ["yellow"],
  service_status: { yellow: "available" },
  available_date_range: { start_date: "2026-01-01", end_date: "2026-01-02" },
  row_counts: {
    fct_trips: 3,
    mart_daily_trip_metrics: 2,
    mart_anomalous_trips: 1,
  },
};

const overview: OverviewMetrics = {
  total_trips: 3,
  total_revenue: 98.5,
  average_fare: 26.67,
  average_duration_minutes: 36.67,
  total_distance: 15,
  airport_trip_count: 1,
  warning_trip_count: 1,
};

const quality: QualitySummary = {
  service: "yellow",
  year: 2026,
  month: 1,
  validated_at: "2026-01-03T10:00:00Z",
  total_rows: 3,
  status_counts: { valid: 1, warning: 1, rejected: 1 },
  rule_counts: { duplicate_record: 1, negative_fare_amount: 1 },
  artifact_name: "validation_2026_01.json",
};

const daily: DailyMetricsResponse = {
  total: 2,
  limit: 10,
  offset: 0,
  items: [
    {
      pickup_date: "2026-01-01",
      trip_count: 2,
      passenger_count: 3,
      trip_distance: 13,
      total_revenue: 83.5,
      average_duration_minutes: 45,
      average_speed_mph: 8,
      airport_trip_count: 1,
    },
    {
      pickup_date: "2026-01-02",
      trip_count: 1,
      passenger_count: 1,
      trip_distance: 2,
      total_revenue: 15,
      average_duration_minutes: 20,
      average_speed_mph: 6,
      airport_trip_count: 0,
    },
  ],
};

const hourly: HourlyDemandResponse = {
  total: 2,
  limit: 24,
  offset: 0,
  items: [
    {
      pickup_date: "2026-01-01",
      pickup_hour: 8,
      trip_count: 1,
      passenger_count: 1,
      average_duration_minutes: 30,
      total_revenue: 23.5,
    },
    {
      pickup_date: "2026-01-01",
      pickup_hour: 9,
      trip_count: 1,
      passenger_count: 2,
      average_duration_minutes: 60,
      total_revenue: 60,
    },
  ],
};

const revenue: RevenueMetricsResponse = {
  total: 2,
  limit: 10,
  offset: 0,
  items: [
    {
      pickup_date: "2026-01-01",
      payment_type: 1,
      trip_count: 2,
      fare_revenue: 68,
      tip_revenue: 11,
      tolls_revenue: 0,
      total_revenue: 83.5,
      average_revenue_per_mile: 6.91,
    },
  ],
};

const zones: ZonesResponse = {
  total: 2,
  limit: 10,
  offset: 0,
  items: [
    {
      zone_id: 1,
      borough: "Manhattan",
      zone_name: "Alpha",
      service_zone: "Yellow Zone",
      is_airport_zone: false,
      pickup_trip_count: 2,
      passenger_count: 3,
      total_revenue: 83.5,
      average_trip_distance: 6.5,
    },
    {
      zone_id: 132,
      borough: "Queens",
      zone_name: "JFK Airport",
      service_zone: "Airports",
      is_airport_zone: true,
      pickup_trip_count: 0,
      passenger_count: 0,
      total_revenue: 0,
      average_trip_distance: null,
    },
  ],
};

const zoneSummary: ZoneSummary = {
  zone_id: 1,
  borough: "Manhattan",
  zone_name: "Alpha",
  service_zone: "Yellow Zone",
  is_airport_zone: false,
  pickup_trip_count: 2,
  dropoff_trip_count: 1,
  related_trip_count: 3,
  total_revenue: 83.5,
  average_trip_distance: 6.5,
  average_duration_minutes: 45,
};

const routes: RoutesResponse = {
  total: 1,
  limit: 10,
  offset: 0,
  items: [
    {
      pickup_zone_id: 1,
      pickup_zone_name: "Alpha",
      dropoff_zone_id: 132,
      dropoff_zone_name: "JFK Airport",
      trip_count: 1,
      average_trip_distance: 10,
      average_duration_minutes: 60,
      total_revenue: 60,
    },
  ],
};

const anomalies: AnomaliesResponse = {
  total: 1,
  limit: 10,
  offset: 0,
  items: [
    {
      trip_id: "trip-2",
      pickup_datetime: "2026-01-01T09:00:00",
      dropoff_datetime: "2026-01-01T10:00:00",
      pickup_zone_id: 1,
      pickup_zone_name: "Alpha",
      dropoff_zone_id: 132,
      dropoff_zone_name: "JFK Airport",
      passenger_count: 2,
      trip_distance: 10,
      fare_amount: 50,
      total_amount: 60,
      duration_minutes: 60,
      average_speed_mph: 10,
      revenue_per_mile: 6,
      is_airport_trip: true,
      quality_status: "warning",
      quality_reasons: "duplicate_record",
    },
  ],
};

export const dashboardFixture: DashboardData = {
  health,
  metadata,
  quality,
  qualityError: null,
  overview,
  daily,
  hourly,
  revenue,
  zones,
  zoneSummary,
  routes,
  anomalies,
};

export function createFetchMock(data: DashboardData = dashboardFixture) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    const body = routeResponse(url, data);
    if (body === undefined) {
      return new Response("Not found", { status: 404 });
    }
    return Response.json(body);
  });
}

function routeResponse(url: string, data: DashboardData): unknown {
  if (url.includes("/health")) return data.health;
  if (url.includes("/metadata")) return data.metadata;
  if (url.includes("/quality/summary")) return data.quality;
  if (url.includes("/metrics/overview")) return data.overview;
  if (url.includes("/metrics/daily")) return data.daily;
  if (url.includes("/metrics/hourly-demand")) return data.hourly;
  if (url.includes("/metrics/revenue")) return data.revenue;
  if (url.includes("/zones/") && url.includes("/summary")) return data.zoneSummary;
  if (url.includes("/zones")) return data.zones;
  if (url.includes("/routes/top")) return data.routes;
  if (url.includes("/anomalies")) return data.anomalies;
  return undefined;
}
