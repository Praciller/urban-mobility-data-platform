export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface HealthResponse {
  status: string;
  duckdb_available: boolean;
  data_freshness: string | null;
  available_marts: string[];
  missing_marts: string[];
}

export interface MetadataResponse {
  supported_services: string[];
  service_status: Record<string, string>;
  available_date_range: DateRange | null;
  row_counts: Record<string, number>;
}

export interface QualitySummary {
  service: string;
  year: number;
  month: number;
  validated_at: string;
  total_rows: number;
  status_counts: {
    valid: number;
    warning: number;
    rejected: number;
  };
  rule_counts: Record<string, number>;
  artifact_name: string;
}

export interface OverviewMetrics {
  total_trips: number;
  total_revenue: number;
  average_fare: number;
  average_duration_minutes: number;
  total_distance: number;
  airport_trip_count: number;
  warning_trip_count: number;
}

export interface PaginatedResponse<ItemT> {
  items: ItemT[];
  total: number;
  limit: number;
  offset: number;
}

export interface DailyMetric {
  pickup_date: string;
  trip_count: number;
  passenger_count: number;
  trip_distance: number;
  total_revenue: number;
  average_duration_minutes: number;
  average_speed_mph: number | null;
  airport_trip_count: number;
}

export interface HourlyDemandMetric {
  pickup_date: string;
  pickup_hour: number;
  trip_count: number;
  passenger_count: number;
  average_duration_minutes: number;
  total_revenue: number;
}

export interface RevenueMetric {
  pickup_date: string;
  payment_type: number;
  trip_count: number;
  fare_revenue: number;
  tip_revenue: number;
  tolls_revenue: number;
  total_revenue: number;
  average_revenue_per_mile: number | null;
}

export interface ZoneMetric {
  zone_id: number;
  borough: string;
  zone_name: string;
  service_zone: string;
  is_airport_zone: boolean;
  pickup_trip_count: number;
  passenger_count: number;
  total_revenue: number;
  average_trip_distance: number | null;
}

export interface ZoneSummary {
  zone_id: number;
  borough: string;
  zone_name: string;
  service_zone: string;
  is_airport_zone: boolean;
  pickup_trip_count: number;
  dropoff_trip_count: number;
  related_trip_count: number;
  total_revenue: number;
  average_trip_distance: number | null;
  average_duration_minutes: number | null;
}

export interface RouteMetric {
  pickup_zone_id: number;
  pickup_zone_name: string;
  dropoff_zone_id: number;
  dropoff_zone_name: string;
  trip_count: number;
  average_trip_distance: number;
  average_duration_minutes: number;
  total_revenue: number;
}

export interface AnomalousTrip {
  trip_id: string;
  pickup_datetime: string;
  dropoff_datetime: string;
  pickup_zone_id: number;
  pickup_zone_name: string;
  dropoff_zone_id: number;
  dropoff_zone_name: string;
  passenger_count: number | null;
  trip_distance: number;
  fare_amount: number;
  total_amount: number;
  duration_minutes: number;
  average_speed_mph: number | null;
  revenue_per_mile: number | null;
  is_airport_trip: boolean;
  quality_status: string;
  quality_reasons: string;
}

export type DailyMetricsResponse = PaginatedResponse<DailyMetric>;
export type HourlyDemandResponse = PaginatedResponse<HourlyDemandMetric>;
export type RevenueMetricsResponse = PaginatedResponse<RevenueMetric>;
export type ZonesResponse = PaginatedResponse<ZoneMetric>;
export type RoutesResponse = PaginatedResponse<RouteMetric>;
export type AnomaliesResponse = PaginatedResponse<AnomalousTrip>;

export interface DashboardData {
  health: HealthResponse;
  metadata: MetadataResponse;
  quality: QualitySummary | null;
  qualityError: string | null;
  overview: OverviewMetrics;
  daily: DailyMetricsResponse;
  hourly: HourlyDemandResponse;
  revenue: RevenueMetricsResponse;
  zones: ZonesResponse;
  routes: RoutesResponse;
  anomalies: AnomaliesResponse;
  zoneSummary: ZoneSummary | null;
}
