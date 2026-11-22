import { describe, expect, test } from "vitest";

import { formatUtcDateTime } from "./format";

describe("formatUtcDateTime", () => {
  test("treats legacy timezone-naive ingestion timestamps as UTC", () => {
    expect(formatUtcDateTime("2026-11-19T10:34:00")).toBe("Nov 19, 2026, 10:34 AM UTC");
  });

  test("normalizes offset timestamps to UTC", () => {
    expect(formatUtcDateTime("2026-11-19T17:34:00+07:00")).toBe("Nov 19, 2026, 10:34 AM UTC");
  });

  test("preserves empty and invalid values", () => {
    expect(formatUtcDateTime(null)).toBe("n/a");
    expect(formatUtcDateTime("not-a-timestamp")).toBe("not-a-timestamp");
  });
});
