import { BarChartPanel } from "../components/Charts";
import { DataTable } from "../components/DataTable";
import { StatCard } from "../components/StatCard";
import type { DashboardData, ZoneMetric } from "../api/types";
import { formatCurrency, formatDuration, formatMiles, formatNumber } from "../lib/format";

export function ZoneAnalyticsPage({ data }: { data: DashboardData }) {
  const summary = data.zoneSummary;

  return (
    <div className="page-stack">
      <section className="page-heading">
        <p className="eyebrow">Zones</p>
        <h2>Zone Analytics</h2>
        <p>
          Pickup demand and local zone summary from <code>/zones</code> and{" "}
          <code>/zones/{"{zone_id}"}/summary</code>.
        </p>
      </section>

      {summary ? (
        <section className="stat-grid">
          <StatCard label="Selected zone" value={summary.zone_name} detail={`${summary.borough} / ${summary.service_zone}`} />
          <StatCard label="Pickups" value={formatNumber(summary.pickup_trip_count)} />
          <StatCard label="Dropoffs" value={formatNumber(summary.dropoff_trip_count)} />
          <StatCard label="Related trips" value={formatNumber(summary.related_trip_count)} />
          <StatCard label="Zone revenue" value={formatCurrency(summary.total_revenue)} />
          <StatCard label="Avg duration" value={formatDuration(summary.average_duration_minutes)} />
        </section>
      ) : null}

      <section className="panel-grid">
        <article className="panel panel--wide">
          <h3>Top pickup zones</h3>
          <BarChartPanel
            bars={[{ key: "pickup_trip_count", name: "Pickups", color: "#2563eb" }]}
            data={data.zones.items.map((zone) => ({ ...zone, label: `${zone.zone_id}: ${zone.zone_name}` }))}
            emptyTitle="No zone metrics available"
            xKey="label"
          />
        </article>
      </section>

      <section className="panel">
        <h3>Zone rows</h3>
        <DataTable<ZoneMetric>
          columns={[
            { header: "Zone", render: (row) => `${row.zone_id} / ${row.zone_name}` },
            { header: "Borough", render: (row) => row.borough },
            { header: "Service zone", render: (row) => row.service_zone },
            { header: "Airport", render: (row) => (row.is_airport_zone ? "Yes" : "No") },
            { header: "Pickups", align: "right", render: (row) => formatNumber(row.pickup_trip_count) },
            { header: "Revenue", align: "right", render: (row) => formatCurrency(row.total_revenue) },
            { header: "Avg distance", align: "right", render: (row) => formatMiles(row.average_trip_distance) },
          ]}
          emptyTitle="No zone metrics available"
          getRowKey={(row) => row.zone_id}
          rows={data.zones.items}
        />
      </section>
    </div>
  );
}
