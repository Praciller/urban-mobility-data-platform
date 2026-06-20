import { BarChartPanel } from "../components/Charts";
import { DataTable } from "../components/DataTable";
import type { DashboardData, RouteMetric } from "../api/types";
import { formatCurrency, formatDuration, formatMiles, formatNumber } from "../lib/format";

export function RouteAnalyticsPage({ data }: { data: DashboardData }) {
  const routeRows = data.routes.items.map((route) => ({
    ...route,
    route_label: `${route.pickup_zone_name} to ${route.dropoff_zone_name}`,
  }));

  return (
    <div className="page-stack">
      <section className="page-heading">
        <p className="eyebrow">Routes</p>
        <h2>Route Analytics</h2>
        <p>Highest-volume origin and destination pairs from the local route mart.</p>
      </section>

      <section className="panel panel--wide">
        <h3>Top route volume</h3>
        <BarChartPanel
          bars={[{ key: "trip_count", name: "Trips", color: "#7c3aed" }]}
          data={routeRows}
          emptyTitle="No route metrics available"
          xKey="route_label"
        />
      </section>

      <section className="panel">
        <h3>Route rows</h3>
        <DataTable<RouteMetric>
          columns={[
            { header: "Pickup", render: (row) => row.pickup_zone_name },
            { header: "Dropoff", render: (row) => row.dropoff_zone_name },
            { header: "Trips", align: "right", render: (row) => formatNumber(row.trip_count) },
            { header: "Distance", align: "right", render: (row) => formatMiles(row.average_trip_distance) },
            { header: "Duration", align: "right", render: (row) => formatDuration(row.average_duration_minutes) },
            { header: "Revenue", align: "right", render: (row) => formatCurrency(row.total_revenue) },
          ]}
          emptyTitle="No route metrics available"
          getRowKey={(row) => `${row.pickup_zone_id}-${row.dropoff_zone_id}`}
          rows={data.routes.items}
        />
      </section>
    </div>
  );
}
