export interface DashboardFilters {
  startDate: string;
  endDate: string;
  limit: number;
}

export const DEFAULT_LIMIT = 10;
export const limitOptions = [10, 25, 50, 100] as const;

export const defaultFilters: DashboardFilters = {
  startDate: "",
  endDate: "",
  limit: DEFAULT_LIMIT,
};

export interface DashboardPage {
  id:
    | "overview"
    | "demand"
    | "zones"
    | "routes"
    | "revenue"
    | "anomalies"
    | "quality";
  label: string;
}

export const dashboardPages: DashboardPage[] = [
  { id: "overview", label: "Overview" },
  { id: "demand", label: "Demand Trends" },
  { id: "zones", label: "Zone Analytics" },
  { id: "routes", label: "Route Analytics" },
  { id: "revenue", label: "Revenue Analytics" },
  { id: "anomalies", label: "Anomaly Explorer" },
  { id: "quality", label: "Data Quality / Pipeline Status" },
];

export type DashboardPageId = DashboardPage["id"];

export function dateQuery(filters: DashboardFilters): Record<string, string> {
  const query: Record<string, string> = {};
  if (filters.startDate) query.start_date = filters.startDate;
  if (filters.endDate) query.end_date = filters.endDate;
  return query;
}
