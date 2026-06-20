import { BarChartPanel, LineChartPanel } from "../components/Charts";
import { DataTable } from "../components/DataTable";
import type { DashboardData, DailyMetric } from "../api/types";
import { formatCurrency, formatDate, formatDuration, formatMiles, formatNumber } from "../lib/format";

export function DemandTrendsPage({ data }: { data: DashboardData }) {
  return (
    <div className="page-stack">
      <section className="page-heading">
        <p className="eyebrow">Demand</p>
        <h2>Demand Trends</h2>
        <p>Daily and hourly demand slices from dbt mart aggregates.</p>
      </section>

      <section className="panel-grid">
        <article className="panel panel--wide">
          <h3>Daily metrics</h3>
          <LineChartPanel
            data={data.daily.items}
            emptyTitle="No daily metrics available"
            lines={[
              { key: "trip_count", name: "Trips", color: "#2563eb" },
              { key: "passenger_count", name: "Passengers", color: "#7c3aed" },
            ]}
            xKey="pickup_date"
          />
        </article>

        <article className="panel">
          <h3>Revenue by day</h3>
          <BarChartPanel
            bars={[{ key: "total_revenue", name: "Revenue", color: "#f59e0b" }]}
            data={data.daily.items}
            emptyTitle="No revenue trend metrics available"
            xKey="pickup_date"
          />
        </article>
      </section>

      <section className="panel">
        <h3>Daily metric rows</h3>
        <DataTable<DailyMetric>
          columns={[
            { header: "Date", render: (row) => formatDate(row.pickup_date) },
            { header: "Trips", align: "right", render: (row) => formatNumber(row.trip_count) },
            { header: "Passengers", align: "right", render: (row) => formatNumber(row.passenger_count) },
            { header: "Distance", align: "right", render: (row) => formatMiles(row.trip_distance) },
            { header: "Revenue", align: "right", render: (row) => formatCurrency(row.total_revenue) },
            { header: "Duration", align: "right", render: (row) => formatDuration(row.average_duration_minutes) },
          ]}
          emptyTitle="No daily metrics available"
          getRowKey={(row) => row.pickup_date}
          rows={data.daily.items}
        />
      </section>
    </div>
  );
}
