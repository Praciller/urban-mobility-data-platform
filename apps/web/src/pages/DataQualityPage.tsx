import { DataTable } from "../components/DataTable";
import { StatCard } from "../components/StatCard";
import type { DashboardData } from "../api/types";
import { formatDate, formatDateTime, formatNumber, formatServices } from "../lib/format";
import { EmptyState } from "../components/StateBlocks";

interface DataQualityPageProps {
  data: DashboardData;
  exportUrl: string;
}

export function DataQualityPage({ data, exportUrl }: DataQualityPageProps) {
  const rowCounts = Object.entries(data.metadata.row_counts).map(([relation, rows]) => ({ relation, rows }));
  const marts = data.health.available_marts.map((mart) => ({ mart, status: "available" }));
  const missing = data.health.missing_marts.map((mart) => ({ mart, status: "missing" }));
  const dateRange = data.metadata.available_date_range;
  const qualityRules = Object.entries(data.quality?.rule_counts ?? {}).map(([rule, rows]) => ({
    rule,
    rows,
  }));

  return (
    <div className="page-stack">
      <section className="page-heading">
        <p className="eyebrow">Pipeline status</p>
        <h2>Data Quality / Pipeline Status</h2>
        <p>Local DuckDB health, mart availability, and row counts from `/health` and `/metadata`.</p>
      </section>

      <section className="stat-grid">
        <StatCard label="API status" value={data.health.status} detail={data.health.duckdb_available ? "DuckDB available" : "DuckDB unavailable"} />
        <StatCard label="Data freshness" value={formatDateTime(data.health.data_freshness)} />
        <StatCard label="Available marts" value={formatNumber(data.health.available_marts.length)} />
        <StatCard label="Missing marts" tone={data.health.missing_marts.length > 0 ? "warning" : "success"} value={formatNumber(data.health.missing_marts.length)} />
        <StatCard label="Rejected rows" tone={data.quality?.status_counts.rejected ? "warning" : "success"} value={formatNumber(data.quality?.status_counts.rejected)} />
        <StatCard label="Warning rows" tone={data.quality?.status_counts.warning ? "warning" : "success"} value={formatNumber(data.quality?.status_counts.warning)} />
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h3>Validation rule evidence</h3>
          {data.quality ? (
            <DataTable
              columns={[
                { header: "Rule", render: (row: { rule: string; rows: number }) => <code>{row.rule}</code> },
                { header: "Rows", align: "right", render: (row: { rule: string; rows: number }) => formatNumber(row.rows) },
              ]}
              emptyTitle="No validation rules fired"
              getRowKey={(row) => row.rule}
              rows={qualityRules}
            />
          ) : (
            <EmptyState
              detail={
                data.qualityError ?? "Run the local demo to create a bounded validation summary."
              }
              title={
                data.qualityError
                  ? "Validation summary unavailable"
                  : "No validation summary available"
              }
            />
          )}
        </article>
        <article className="panel">
          <h3>Latest validation artifact</h3>
          {data.quality ? (
            <div className="metadata-grid metadata-grid--compact">
              <div><span>Artifact</span><strong>{data.quality.artifact_name}</strong></div>
              <div><span>Dataset</span><strong>{`${data.quality.service} ${data.quality.year}-${String(data.quality.month).padStart(2, "0")}`}</strong></div>
              <div><span>Validated</span><strong>{formatDateTime(data.quality.validated_at)}</strong></div>
              <div><span>Total rows</span><strong>{formatNumber(data.quality.total_rows)}</strong></div>
            </div>
          ) : (
            <EmptyState
              detail={data.qualityError ?? undefined}
              title={
                data.qualityError
                  ? "Validation artifact unreadable"
                  : "No pipeline artifact available"
              }
            />
          )}
        </article>
      </section>

      <section className="panel-grid">
        <article className="panel">
          <h3>Mart status</h3>
          <DataTable
            columns={[
              { header: "Mart", render: (row: { mart: string; status: string }) => row.mart },
              { header: "Status", render: (row: { mart: string; status: string }) => row.status },
            ]}
            emptyTitle="No mart metadata available"
            getRowKey={(row) => row.mart}
            rows={[...marts, ...missing]}
          />
        </article>
        <article className="panel">
          <h3>Relation row counts</h3>
          <DataTable
            columns={[
              { header: "Relation", render: (row: { relation: string; rows: number }) => row.relation },
              { header: "Rows", align: "right", render: (row: { relation: string; rows: number }) => formatNumber(row.rows) },
            ]}
            emptyTitle="No row counts available"
            getRowKey={(row) => row.relation}
            rows={rowCounts}
          />
        </article>
      </section>

      <section className="panel">
        <h3>Dataset metadata</h3>
        <div className="metadata-grid">
          <div>
            <span>Service</span>
            <strong>{formatServices(data.metadata.supported_services)}</strong>
          </div>
          <div>
            <span>Date range</span>
            <strong>
              {dateRange
                ? `${formatDate(dateRange.start_date)} to ${formatDate(dateRange.end_date)}`
                : "n/a"}
            </strong>
          </div>
          <div>
            <span>Storage mode</span>
            <strong>Local persisted dataset</strong>
          </div>
          <div>
            <span>dbt readiness</span>
            <strong>
              {data.health.missing_marts.length === 0
                ? `${data.health.available_marts.length} marts ready`
                : `${data.health.missing_marts.length} marts missing`}
            </strong>
          </div>
        </div>
      </section>

      <section className="panel">
        <h3>Local export</h3>
        <p>Download a bounded CSV from the read-only API. The dashboard does not write back to the API.</p>
        <a className="button button--primary" href={exportUrl}>
          Download daily metrics CSV
        </a>
        <p className="path-note">DuckDB is opened read-only by the local analytics API.</p>
      </section>
    </div>
  );
}
