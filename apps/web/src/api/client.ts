import type {
  AnomaliesResponse,
  DashboardData,
  DailyMetricsResponse,
  HealthResponse,
  HourlyDemandResponse,
  MetadataResponse,
  OverviewMetrics,
  PaginatedResponse,
  QualitySummary,
  RevenueMetricsResponse,
  RoutesResponse,
  ZonesResponse,
  ZoneSummary,
} from "./types";
import type { DashboardFilters } from "../lib/filters";
import { dateQuery } from "../lib/filters";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

type QueryValue = string | number | boolean | null | undefined;
type QueryParams = Record<string, QueryValue>;

export class ApiError extends Error {
  readonly status?: number;
  readonly endpoint: string;

  constructor(message: string, endpoint: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.endpoint = endpoint;
    this.status = status;
  }
}

export function getApiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL?.trim();
  return (configured || DEFAULT_API_BASE_URL).replace(/\/+$/, "");
}

export function buildApiUrl(path: string, params: QueryParams = {}): string {
  const url = new URL(path, `${getApiBaseUrl()}/`);
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    url.searchParams.set(key, String(value));
  });
  return url.toString();
}

export async function requestJson<ResponseT>(
  path: string,
  params: QueryParams = {},
  signal?: AbortSignal,
): Promise<ResponseT> {
  const url = buildApiUrl(path, params);
  const response = await fetch(url, {
    headers: { Accept: "application/json" },
    signal,
  });

  if (!response.ok) {
    const detail = await readErrorDetail(response);
    throw new ApiError(detail || `Request failed with HTTP ${response.status}`, path, response.status);
  }

  return (await response.json()) as ResponseT;
}

export async function fetchDashboardData(
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<Omit<DashboardData, "zoneSummary">> {
  const common = dateQuery(filters);
  const limit = filters.limit;

  const [
    health,
    metadata,
    qualityResult,
    overview,
    daily,
    hourly,
    revenue,
    zones,
    routes,
    anomalies,
  ] = await Promise.all([
    requestJson<HealthResponse>("/health", {}, signal),
    requestJson<MetadataResponse>("/metadata", {}, signal),
    requestQualitySummary(signal),
    requestOverviewOrEmpty(common, signal),
    requestPageOrEmpty<DailyMetricsResponse>(
      "/metrics/daily",
      { limit, ...common, sort_by: "pickup_date", sort_order: "asc" },
      limit,
      signal,
    ),
    requestPageOrEmpty<HourlyDemandResponse>(
      "/metrics/hourly-demand",
      { limit: Math.max(24, limit), ...common, sort_by: "pickup_hour", sort_order: "asc" },
      Math.max(24, limit),
      signal,
    ),
    requestPageOrEmpty<RevenueMetricsResponse>(
      "/metrics/revenue",
      { limit, ...common, sort_by: "pickup_date", sort_order: "asc" },
      limit,
      signal,
    ),
    requestPageOrEmpty<ZonesResponse>(
      "/zones",
      { limit, sort_by: "pickup_trip_count", sort_order: "desc" },
      limit,
      signal,
    ),
    requestPageOrEmpty<RoutesResponse>(
      "/routes/top",
      { limit, sort_by: "trip_count", sort_order: "desc" },
      limit,
      signal,
    ),
    requestPageOrEmpty<AnomaliesResponse>(
      "/anomalies",
      { limit, ...common, sort_by: "pickup_datetime", sort_order: "desc" },
      limit,
      signal,
    ),
  ]);

  return {
    health,
    metadata,
    quality: qualityResult.data,
    qualityError: qualityResult.error,
    overview,
    daily,
    hourly,
    revenue,
    zones,
    routes,
    anomalies,
  };
}

async function requestQualitySummary(
  signal?: AbortSignal,
): Promise<{ data: QualitySummary | null; error: string | null }> {
  try {
    const data = await requestJson<QualitySummary>("/quality/summary", {}, signal);
    return { data, error: null };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { data: null, error: null };
    }
    if (error instanceof ApiError && error.status === 503) {
      return { data: null, error: error.message };
    }
    throw error;
  }
}

async function requestOverviewOrEmpty(
  params: QueryParams,
  signal?: AbortSignal,
): Promise<OverviewMetrics> {
  try {
    return await requestJson<OverviewMetrics>("/metrics/overview", params, signal);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return {
        total_trips: 0,
        total_revenue: 0,
        average_fare: 0,
        average_duration_minutes: 0,
        total_distance: 0,
        airport_trip_count: 0,
        warning_trip_count: 0,
      };
    }
    throw error;
  }
}

async function requestPageOrEmpty<ResponseT extends PaginatedResponse<unknown>>(
  path: string,
  params: QueryParams,
  limit: number,
  signal?: AbortSignal,
): Promise<ResponseT> {
  try {
    return await requestJson<ResponseT>(path, params, signal);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { items: [], total: 0, limit, offset: 0 } as unknown as ResponseT;
    }
    throw error;
  }
}

export function fetchZoneSummary(
  zoneId: number,
  filters: DashboardFilters,
  signal?: AbortSignal,
): Promise<ZoneSummary> {
  return requestJson<ZoneSummary>(`/zones/${zoneId}/summary`, dateQuery(filters), signal);
}

export function dailyMetricsCsvUrl(filters: DashboardFilters): string {
  return buildApiUrl("/exports/daily-metrics.csv", dateQuery(filters));
}

async function readErrorDetail(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string") return payload.detail;
    if (Array.isArray(payload.detail)) return payload.detail.map(String).join(", ");
  } catch {
    return response.statusText;
  }
  return response.statusText;
}
