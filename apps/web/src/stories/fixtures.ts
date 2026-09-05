import type { HealthResponse, MetadataResponse } from "../api/types";
import type { DashboardFilters } from "../lib/filters";

export interface StoryTrip {
  distance: number;
  fare: number;
  pickup: string;
  route: string;
  status: string;
}

export interface StoryTrend {
  label: string;
  revenue: number;
  trips: number;
}

export const storyFilters: DashboardFilters = {
  endDate: "2026-01-31",
  limit: 25,
  startDate: "2026-01-01",
};

export const storyHealth: HealthResponse = {
  available_marts: ["fct_trips", "daily_metrics", "hourly_demand"],
  data_freshness: "2026-01-02T10:30:00Z",
  duckdb_available: true,
  missing_marts: [],
  status: "ok",
};

export const storyMetadata: MetadataResponse = {
  available_date_range: { end_date: "2026-01-31", start_date: "2026-01-01" },
  row_counts: { fct_trips: 128430 },
  service_status: { yellow: "available" },
  supported_services: ["yellow"],
};

export const storyTrips: StoryTrip[] = [
  { distance: 3.2, fare: 18.5, pickup: "08:15", route: "Midtown → Astoria", status: "Valid" },
  { distance: 7.8, fare: 32.75, pickup: "09:40", route: "SoHo → JFK Airport", status: "Warning" },
  {
    distance: 2.1,
    fare: 14.25,
    pickup: "10:05",
    route: "Harlem → Upper East Side",
    status: "Valid",
  },
];

export const storyTrends: StoryTrend[] = [
  { label: "Jan 01", revenue: 12400, trips: 920 },
  { label: "Jan 02", revenue: 13750, trips: 1010 },
  { label: "Jan 03", revenue: 11980, trips: 870 },
  { label: "Jan 04", revenue: 15120, trips: 1140 },
];
