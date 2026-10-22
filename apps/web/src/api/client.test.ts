import { afterEach, describe, expect, test, vi } from "vitest";

import { fetchDailyTrend } from "./client";
import type { DailyMetric } from "./types";

const metric = (index: number): DailyMetric => ({
  pickup_date: `2026-01-${String((index % 28) + 1).padStart(2, "0")}`,
  trip_count: 1,
  passenger_count: 1,
  trip_distance: 3,
  total_revenue: 23.5,
  average_duration_minutes: 30,
  average_speed_mph: 6,
  airport_trip_count: 1,
});

describe("daily trend pagination", () => {
  afterEach(() => vi.unstubAllGlobals());

  test("fetches all trend pages independently of table row limits", async () => {
    const offsets: number[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = new URL(String(input));
        const offset = Number(url.searchParams.get("offset") ?? "0");
        offsets.push(offset);
        expect(url.searchParams.get("limit")).toBe("500");
        expect(url.searchParams.get("start_date")).toBe("2026-01-01");
        const remaining = Math.max(0, 502 - offset);
        return Response.json({
          items: Array.from({ length: Math.min(500, remaining) }, (_, i) => metric(offset + i)),
          total: 502,
          limit: 500,
          offset,
        });
      }),
    );

    const result = await fetchDailyTrend({ start_date: "2026-01-01" });
    expect(result).toHaveLength(502);
    expect(offsets).toEqual([0, 500]);
  });

  test("returns empty results without treating HTTP 404 as a failure", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => Response.json({}, { status: 404 })),
    );
    await expect(fetchDailyTrend({})).resolves.toEqual([]);
  });
});
