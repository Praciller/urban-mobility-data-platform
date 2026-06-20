import { DataTable } from "../components/DataTable";
import type { AnomalousTrip, DashboardData } from "../api/types";
import { formatCurrency, formatDateTime, formatDuration, formatMiles, formatNumber } from "../lib/format";

export function AnomalyExplorerPage({ data }: { data: DashboardData }) {
  return (
    <div className="page-stack">
      <section className="page-heading">
        <p className="eyebrow">Quality warnings</p>
        <h2>Anomaly Explorer</h2>
        <p>Explainable warning rows from validation and dbt anomaly marts.</p>
      </section>

      <section className="panel">
        <h3>Anomalous trip rows</h3>
        <DataTable<AnomalousTrip>
          columns={[
            { header: "Trip ID", render: (row) => row.trip_id },
            { header: "Pickup", render: (row) => formatDateTime(row.pickup_datetime) },
            { header: "Route", render: (row) => `${row.pickup_zone_name} to ${row.dropoff_zone_name}` },
            { header: "Passengers", align: "right", render: (row) => formatNumber(row.passenger_count) },
            { header: "Distance", align: "right", render: (row) => formatMiles(row.trip_distance) },
            { header: "Duration", align: "right", render: (row) => formatDuration(row.duration_minutes) },
            { header: "Total", align: "right", render: (row) => formatCurrency(row.total_amount) },
            { header: "Reasons", render: (row) => <code>{row.quality_reasons}</code> },
          ]}
          emptyDetail="Validation produced no warning rows for the active filters."
          emptyTitle="No anomalies available"
          getRowKey={(row) => row.trip_id}
          rows={data.anomalies.items}
        />
      </section>
    </div>
  );
}
