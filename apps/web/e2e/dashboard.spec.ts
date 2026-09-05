import { expect, test, type Page } from "@playwright/test";

const dashboardPages = [
  ["Overview", "Overview"],
  ["Demand Trends", "Demand Trends"],
  ["Zone Analytics", "Zone Analytics"],
  ["Route Analytics", "Route Analytics"],
  ["Revenue Analytics", "Revenue Analytics"],
  ["Anomaly Explorer", "Anomaly Explorer"],
  ["Data Quality / Pipeline Status", "Data Quality / Pipeline Status"],
] as const;
const apiPort = process.env.URBAN_MOBILITY_E2E_API_PORT ?? "8000";

async function openNavigationIfCompact(page: Page): Promise<void> {
  const toggle = page.getByRole("button", { name: "Open dashboard navigation" });
  if (await toggle.isVisible()) await toggle.click();
}

function captureBrowserErrors(page: Page): string[] {
  const browserErrors: string[] = [];
  page.on("pageerror", (error) => browserErrors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  return browserErrors;
}

test.describe("sample-backed mobility dashboard", () => {
  test("loads health, KPI content, and all dashboard pages", async ({ page }) => {
    const browserErrors = captureBrowserErrors(page);
    await page.goto("/");
    await expect(page.getByText("DuckDB connected")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("$47.00")).toBeVisible();
    expect(browserErrors).toEqual([]);

    for (const [label, heading] of dashboardPages) {
      await openNavigationIfCompact(page);
      const navigationButton = page.getByRole("button", { name: label, exact: true });
      await navigationButton.click();
      await expect(page.getByRole("heading", { name: heading, exact: true })).toBeVisible();
      await openNavigationIfCompact(page);
      await expect(page.getByRole("button", { name: label, exact: true })).toHaveAttribute(
        "aria-current",
        "page",
      );
    }
  });

  test("applies date and row-limit filters through the visible controls", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

    const limitRequest = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return url.pathname.endsWith("/zones") && url.searchParams.get("limit") === "25";
    });
    await page.getByLabel("Rows per table").selectOption("25");
    await limitRequest;

    const dateRequest = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return (
        url.pathname.endsWith("/metrics/daily") &&
        url.searchParams.get("start_date") === "2026-01-01"
      );
    });
    await page.getByLabel("Start date").fill("2026-01-01");
    await dateRequest;
    await expect(page.getByText(/Data range 2026-01-01/)).toBeVisible();
  });

  test("shows anomaly and data-quality evidence", async ({ page }) => {
    await page.goto("/");
    await openNavigationIfCompact(page);
    await page.getByRole("button", { name: "Anomaly Explorer", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Anomaly Explorer" })).toBeVisible();
    await expect(page.getByText("duplicate_record")).toBeVisible();

    await openNavigationIfCompact(page);
    await page.getByRole("button", { name: "Data Quality / Pipeline Status", exact: true }).click();
    await expect(
      page.getByRole("heading", { name: "Data Quality / Pipeline Status" }),
    ).toBeVisible();
    await expect(page.getByText("Rejected rows")).toBeVisible();
    await expect(page.getByText("Warning rows")).toBeVisible();
  });

  test("recovers from an API-unavailable state through Retry", async ({ page }) => {
    await page.route(`http://127.0.0.1:${apiPort}/**`, (route) => route.abort());
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "API unavailable" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();

    await page.unroute(`http://127.0.0.1:${apiPort}/**`);
    await page.getByRole("button", { name: "Retry" }).click();
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.getByText("DuckDB connected")).toBeVisible();
  });

  test("supports compact navigation without app-shell overflow", async ({ page }, testInfo) => {
    test.skip(testInfo.project.name !== "mobile-chromium", "This seam is mobile-specific.");
    await page.goto("/");
    const toggle = page.getByRole("button", { name: "Open dashboard navigation" });
    await expect(toggle).toHaveAttribute("aria-expanded", "false");

    await toggle.focus();
    await expect(toggle).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Close dashboard navigation" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );

    await page.getByRole("button", { name: "Demand Trends", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Demand Trends" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Open dashboard navigation" })).toHaveAttribute(
      "aria-expanded",
      "false",
    );

    const dimensions = await page.evaluate(() => ({
      clientWidth: document.documentElement.clientWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth);
  });
});
