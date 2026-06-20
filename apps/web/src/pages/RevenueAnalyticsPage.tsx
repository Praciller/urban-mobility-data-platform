import { BarChartPanel } from "../components/Charts";
import { DataTable } from "../components/DataTable";
import type { DashboardData, RevenueMetric } from "../api/types";
import { formatCurrency, formatDate, formatNumber, formatPaymentType } from "../lib/format";

export function RevenueAnalyticsPage({ data }: { data: DashboardData }) {
  return (
    <div className="page-stack">
      <section className="page-heading">
        <p className="eyebrow">Revenue</p>
        <h2>Revenue Analytics</h2>
        <p>Payment-type and revenue-per-mile metrics from `/metrics/revenue`.</p>
      </section>

      <section className="panel-grid">
        <article className="panel panel--wide">
          <h3>Total revenue by date and payment type</h3>
          <BarChartPanel
            bars={[{ key: "total_revenue", name: "Total revenue", color: "#f59e0b" }]}
            data={data.revenue.items.map((row) => ({
              ...row,
              label: `${row.pickup_date} / ${formatPaymentType(row.payment_type)}`,
            }))}
            emptyTitle="No revenue metrics available"
            xKey="label"
          />
        </article>
      </section>

      <section className="panel">
        <h3>Revenue rows</h3>
        <DataTable<RevenueMetric>
          columns={[
            { header: "Date", render: (row) => formatDate(row.pickup_date) },
            { header: "Payment", render: (row) => formatPaymentType(row.payment_type) },
            { header: "Trips", align: "right", render: (row) => formatNumber(row.trip_count) },
            { header: "Fare", align: "right", render: (row) => formatCurrency(row.fare_revenue) },
            { header: "Tips", align: "right", render: (row) => formatCurrency(row.tip_revenue) },
            { header: "Tolls", align: "right", render: (row) => formatCurrency(row.tolls_revenue) },
            { header: "Total", align: "right", render: (row) => formatCurrency(row.total_revenue) },
          ]}
          emptyTitle="No revenue metrics available"
          getRowKey={(row) => `${row.pickup_date}-${row.payment_type}`}
          rows={data.revenue.items}
        />
      </section>
    </div>
  );
}
