import { useState, type ReactNode } from "react";

import { dashboardPages, limitOptions } from "../lib/filters";
import type { DashboardFilters, DashboardPageId } from "../lib/filters";
import { formatDateTime } from "../lib/format";
import type { HealthResponse, MetadataResponse } from "../api/types";

interface AppShellProps {
  activePage: DashboardPageId;
  children: ReactNode;
  exportUrl: string;
  filters: DashboardFilters;
  health?: HealthResponse;
  metadata?: MetadataResponse;
  isLoading: boolean;
  onFilterChange: (filters: Partial<DashboardFilters>) => void;
  onPageChange: (page: DashboardPageId) => void;
  onReload: () => void;
}

export function AppShell({
  activePage,
  children,
  exportUrl,
  filters,
  health,
  metadata,
  isLoading,
  onFilterChange,
  onPageChange,
  onReload,
}: AppShellProps) {
  const [isNavigationOpen, setIsNavigationOpen] = useState(false);
  const dateRange = metadata?.available_date_range;

  return (
    <div className="app-shell">
      <div className="mobile-nav-bar">
        <span className="mobile-nav-label">Dashboard navigation</span>
        <button
          aria-controls="dashboard-navigation"
          aria-expanded={isNavigationOpen}
          className="mobile-nav-toggle"
          onClick={() => setIsNavigationOpen((isOpen) => !isOpen)}
          type="button"
        >
          {isNavigationOpen ? "Close dashboard navigation" : "Open dashboard navigation"}
        </button>
      </div>

      <aside
        className={isNavigationOpen ? "sidebar sidebar--open" : "sidebar"}
        id="dashboard-navigation"
        aria-label="Primary dashboard navigation"
      >
        <div className="brand">
          <span className="brand-mark">UM</span>
          <div>
            <strong>Urban Mobility</strong>
            <small>Local analytics dashboard</small>
          </div>
        </div>
        <nav aria-label="Dashboard pages">
          {dashboardPages.map((page) => (
            <button
              className={activePage === page.id ? "nav-link nav-link--active" : "nav-link"}
              key={page.id}
              onClick={() => {
                onPageChange(page.id);
                setIsNavigationOpen(false);
              }}
              aria-current={activePage === page.id ? "page" : undefined}
              type="button"
            >
              {page.label}
            </button>
          ))}
        </nav>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <div>
            <h1>NYC TLC Mobility Intelligence</h1>
            <p className="subtitle">
              Read-only dashboard over local DuckDB marts and the FastAPI analytics API.
            </p>
          </div>
          <div className="status-stack">
            <span
              className={health?.duckdb_available ? "status-pill status-pill--ok" : "status-pill"}
              role="status"
            >
              {health?.duckdb_available ? "DuckDB connected" : "DuckDB status pending"}
            </span>
            <small>
              {health?.data_freshness
                ? `Freshness ${formatDateTime(health.data_freshness)}`
                : "Local sample mode"}
            </small>
          </div>
        </header>

        <section className="controls" aria-label="Dashboard filters">
          <label>
            Start date
            <input
              aria-label="Start date"
              onChange={(event) => onFilterChange({ startDate: event.target.value })}
              type="date"
              value={filters.startDate}
            />
          </label>
          <label>
            End date
            <input
              aria-label="End date"
              onChange={(event) => onFilterChange({ endDate: event.target.value })}
              type="date"
              value={filters.endDate}
            />
          </label>
          <label>
            Rows per table
            <select
              aria-label="Rows per table"
              onChange={(event) => onFilterChange({ limit: Number(event.target.value) })}
              value={filters.limit}
            >
              {limitOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
          </label>
          <button className="button" disabled={isLoading} onClick={onReload} type="button">
            Refresh
          </button>
          <a className="button button--secondary" href={exportUrl}>
            Export daily CSV
          </a>
          {dateRange ? (
            <p className="range-note">
              Data range {dateRange.start_date} to {dateRange.end_date}
            </p>
          ) : null}
        </section>

        <main>{children}</main>
      </div>
    </div>
  );
}
