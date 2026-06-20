import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { App } from "./App";
import { createFetchMock, dashboardFixture } from "./test/mockApi";

describe("Urban mobility dashboard", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", createFetchMock());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  test("renders overview KPIs with mocked analytics data", async () => {
    render(<App />);

    expect(screen.getByText("Loading local mobility analytics")).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByText("$98.50")).toBeInTheDocument();
    expect(screen.getByText("$26.67")).toBeInTheDocument();
    expect(screen.getByText("36.7 min")).toBeInTheDocument();
    expect(screen.getByText("Yellow Taxi only")).toBeInTheDocument();
  });

  test("renders API unavailable state when requests fail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("offline"))));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "API unavailable" })).toBeInTheDocument();
    expect(screen.getByText(/Start the local FastAPI service/i)).toBeInTheDocument();
  });

  test("renders empty state for charts when an endpoint returns no rows", async () => {
    vi.stubGlobal(
      "fetch",
      createFetchMock({
        ...dashboardFixture,
        daily: { items: [], total: 0, limit: 10, offset: 0 },
      }),
    );

    render(<App />);

    expect(await screen.findByText("No daily metrics available")).toBeInTheDocument();
  });

  test("renders anomaly table with quality reasons", async () => {
    render(<App />);

    await userEvent.click(await screen.findByRole("button", { name: "Anomaly Explorer" }));

    expect(await screen.findByRole("heading", { name: "Anomaly Explorer" })).toBeInTheDocument();
    expect(screen.getByText("trip-2")).toBeInTheDocument();
    expect(screen.getByText("duplicate_record")).toBeInTheDocument();
  });

  test("keeps the dashboard usable when no anomaly rows exist", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/anomalies")) {
        return Response.json({ detail: "No anomalous trips found" }, { status: 404 });
      }
      return fetchMock(input);
    }));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Anomaly Explorer" }));
    expect(screen.getByText("No anomalies available")).toBeInTheDocument();
  });

  test("renders a filtered empty state when overview metrics have no rows", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/metrics/overview")) {
        return Response.json({ detail: "No overview metrics found" }, { status: 404 });
      }
      return fetchMock(input);
    }));

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(screen.getByText("No overview metrics available")).toBeInTheDocument();
  });

  test("renders dataset and pipeline metadata", async () => {
    render(<App />);

    await userEvent.click(
      await screen.findByRole("button", { name: "Data Quality / Pipeline Status" }),
    );

    expect(await screen.findByRole("heading", { name: "Dataset metadata" })).toBeInTheDocument();
    expect(screen.getByText("Yellow Taxi only")).toBeInTheDocument();
    expect(screen.getByText("2026-01-01 to 2026-01-02")).toBeInTheDocument();
    expect(screen.getByText("Local persisted dataset")).toBeInTheDocument();
  });

  test("renders rejected-record counts and validation rule evidence", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/quality/summary")) {
        return Response.json({
          service: "yellow",
          year: 2026,
          month: 1,
          validated_at: "2026-01-03T10:00:00Z",
          total_rows: 3,
          status_counts: { valid: 1, warning: 1, rejected: 1 },
          rule_counts: { duplicate_record: 1, negative_fare_amount: 1 },
          artifact_name: "validation_2026_01.json",
        });
      }
      return fetchMock(input);
    }));

    render(<App />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Data Quality / Pipeline Status" }),
    );

    expect(screen.getByText("Rejected rows")).toBeInTheDocument();
    expect(screen.getByText("negative_fare_amount")).toBeInTheDocument();
    expect(screen.getByText("validation_2026_01.json")).toBeInTheDocument();
  });

  test("surfaces an invalid quality artifact without hiding healthy analytics", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo | URL) => {
      if (String(input).includes("/quality/summary")) {
        return Response.json(
          { detail: "The latest validation summary has inconsistent row counts" },
          { status: 503 },
        );
      }
      return fetchMock(input);
    }));

    render(<App />);
    await userEvent.click(
      await screen.findByRole("button", { name: "Data Quality / Pipeline Status" }),
    );

    expect(await screen.findByText("Validation summary unavailable")).toBeInTheDocument();
    expect(screen.getAllByText(/inconsistent row counts/i)).toHaveLength(2);
  });

  test("updates API limit parameter from the dashboard control", async () => {
    const fetchMock = createFetchMock();
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    await screen.findByRole("heading", { name: "Overview" });
    await userEvent.selectOptions(screen.getByLabelText("Rows per table"), "25");

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/zones?limit=25"),
        expect.any(Object),
      );
    });
  });
});
