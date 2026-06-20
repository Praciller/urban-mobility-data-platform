import { lazy, Suspense, useEffect, useMemo, useState } from "react";

import { dailyMetricsCsvUrl, fetchDashboardData, fetchZoneSummary } from "./api/client";
import type { DashboardData } from "./api/types";
import { AppShell } from "./components/AppShell";
import { ErrorState, LoadingState } from "./components/StateBlocks";
import { defaultFilters } from "./lib/filters";
import type { DashboardFilters, DashboardPageId } from "./lib/filters";

const AnomalyExplorerPage = lazy(() =>
  import("./pages/AnomalyExplorerPage").then((module) => ({
    default: module.AnomalyExplorerPage,
  })),
);
const DataQualityPage = lazy(() =>
  import("./pages/DataQualityPage").then((module) => ({ default: module.DataQualityPage })),
);
const DemandTrendsPage = lazy(() =>
  import("./pages/DemandTrendsPage").then((module) => ({ default: module.DemandTrendsPage })),
);
const OverviewPage = lazy(() =>
  import("./pages/OverviewPage").then((module) => ({ default: module.OverviewPage })),
);
const RevenueAnalyticsPage = lazy(() =>
  import("./pages/RevenueAnalyticsPage").then((module) => ({
    default: module.RevenueAnalyticsPage,
  })),
);
const RouteAnalyticsPage = lazy(() =>
  import("./pages/RouteAnalyticsPage").then((module) => ({
    default: module.RouteAnalyticsPage,
  })),
);
const ZoneAnalyticsPage = lazy(() =>
  import("./pages/ZoneAnalyticsPage").then((module) => ({ default: module.ZoneAnalyticsPage })),
);

export function App() {
  const [activePage, setActivePage] = useState<DashboardPageId>("overview");
  const [filters, setFilters] = useState<DashboardFilters>(defaultFilters);
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [reloadToken, setReloadToken] = useState(0);

  const exportUrl = useMemo(() => dailyMetricsCsvUrl(filters), [filters]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadDashboard(): Promise<void> {
      setIsLoading(true);
      setError(null);

      try {
        const dashboard = await fetchDashboardData(filters, controller.signal);
        const firstZone = dashboard.zones.items[0];
        const zoneSummary = firstZone
          ? await fetchZoneSummary(firstZone.zone_id, filters, controller.signal)
          : null;

        setData({ ...dashboard, zoneSummary });
      } catch (caught) {
        if (controller.signal.aborted) return;
        setData(null);
        setError(caught instanceof Error ? caught.message : "Unable to load dashboard data");
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }

    void loadDashboard();
    return () => controller.abort();
  }, [filters, reloadToken]);

  function updateFilters(nextFilters: Partial<DashboardFilters>): void {
    setFilters((current) => ({ ...current, ...nextFilters }));
  }

  function renderPage() {
    if (!data) {
      return <LoadingState />;
    }

    switch (activePage) {
      case "demand":
        return <DemandTrendsPage data={data} />;
      case "zones":
        return <ZoneAnalyticsPage data={data} />;
      case "routes":
        return <RouteAnalyticsPage data={data} />;
      case "revenue":
        return <RevenueAnalyticsPage data={data} />;
      case "anomalies":
        return <AnomalyExplorerPage data={data} />;
      case "quality":
        return <DataQualityPage data={data} exportUrl={exportUrl} />;
      case "overview":
      default:
        return <OverviewPage data={data} />;
    }
  }

  return (
    <AppShell
      activePage={activePage}
      exportUrl={exportUrl}
      filters={filters}
      health={data?.health}
      isLoading={isLoading}
      metadata={data?.metadata}
      onFilterChange={updateFilters}
      onPageChange={setActivePage}
      onReload={() => setReloadToken((current) => current + 1)}
    >
      {error ? (
        <ErrorState message={error} onRetry={() => setReloadToken((current) => current + 1)} />
      ) : isLoading && !data ? (
        <LoadingState />
      ) : (
        <Suspense fallback={<LoadingState />}>{renderPage()}</Suspense>
      )}
    </AppShell>
  );
}
