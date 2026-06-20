import { BarChartPanel, LineChartPanel } from "../components/Charts";
import { EmptyState } from "../components/StateBlocks";
import { StatCard } from "../components/StatCard";
import type { DashboardData } from "../api/types";
import {
  formatCompactNumber,
  formatCurrency,
  formatDuration,
  formatMiles,
  formatNumber,
  formatServices,
} from "../lib/format";

export function OverviewPage({ data }: { data: DashboardData }) {
  const { overview, daily, hourly, metadata } = data;

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Portfolio MVP</p>
          <h2>Overview</h2>
          <p>
            <strong className="inline-highlight">{formatServices(metadata.supported_services)}</strong>
            <span> with local sample data, read-only API calls, and no cloud dependencies.</span>
          </p>
        </div>
        <div className="hero-meta">
          <span>{formatNumber(metadata.row_counts.fct_trips)} fact rows</span>
          <span>{formatNumber(data.health.available_marts.length)} available marts</span>
        </div>
      </section>

      {overview.total_trips === 0 ? (
        <EmptyState
          detail="Adjust the date filters or rerun the bounded local demo."
          title="No overview metrics available"
        />
      ) : (
        <>
          <section className="stat-grid">
            <StatCard label="Trips" value={formatCompactNumber(overview.total_trips)} detail="Filtered total" />
            <StatCard label="Revenue" value={formatCurrency(overview.total_revenue)} detail="Total amount" />
            <StatCard label="Average fare" value={formatCurrency(overview.average_fare)} detail="Per trip" />
            <StatCard label="Average duration" value={formatDuration(overview.average_duration_minutes)} detail="Trip time" />
            <StatCard label="Distance" value={formatMiles(overview.total_distance)} detail="Total miles" />
            <StatCard
              detail={`${formatNumber(overview.warning_trip_count)} warning trips`}
              label="Airport trips"
              tone={overview.warning_trip_count > 0 ? "warning" : "success"}
              value={formatNumber(overview.airport_trip_count)}
            />
          </section>

          <section className="panel-grid">
            <article className="panel panel--wide">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Demand</p>
                  <h3>Daily trip and revenue trend</h3>
                </div>
              </div>
              <LineChartPanel
                data={daily.items}
                emptyTitle="No daily metrics available"
                lines={[
                  { key: "trip_count", name: "Trips", color: "#2563eb" },
                  { key: "total_revenue", name: "Revenue", color: "#f59e0b" },
                ]}
                xKey="pickup_date"
              />
            </article>

            <article className="panel">
              <div className="panel-heading">
                <div>
                  <p className="eyebrow">Hourly demand</p>
                  <h3>Pickup volume by hour</h3>
                </div>
              </div>
              <BarChartPanel
                bars={[{ key: "trip_count", name: "Trips", color: "#0f766e" }]}
                data={hourly.items}
                emptyTitle="No hourly demand metrics available"
                xKey="pickup_hour"
              />
            </article>
          </section>
        </>
      )}
    </div>
  );
}
