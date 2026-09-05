import os from "node:os";
import path from "node:path";

import { defineConfig, devices } from "@playwright/test";

const repositoryRoot = path.resolve(import.meta.dirname, "..", "..");
const dataDirectory =
  process.env.URBAN_MOBILITY_E2E_DATA_DIR ?? path.join(os.tmpdir(), "urban-mobility-web-e2e");
const duckdbPath = path.join(dataDirectory, "processed", "urban_mobility.duckdb");
const apiPort = process.env.URBAN_MOBILITY_E2E_API_PORT ?? "8000";
const apiBaseUrl = `http://127.0.0.1:${apiPort}`;

export default defineConfig({
  forbidOnly: Boolean(process.env.CI),
  fullyParallel: false,
  outputDir: "test-results",
  reporter: [["list"], ["html", { open: "never", outputFolder: "playwright-report" }]],
  retries: process.env.CI ? 1 : 0,
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  workers: 1,
  projects: [
    {
      name: "desktop-chromium",
      use: { ...devices["Desktop Chrome"], viewport: { height: 900, width: 1440 } },
    },
    {
      name: "mobile-chromium",
      use: { ...devices["Desktop Chrome"], viewport: { height: 844, width: 390 } },
    },
  ],
  webServer: [
    {
      command: `uv run uvicorn apps.api.app.main:app --host 127.0.0.1 --port ${apiPort}`,
      cwd: repositoryRoot,
      env: { DATA_DIR: dataDirectory, DUCKDB_PATH: duckdbPath },
      reuseExistingServer: false,
      timeout: 120_000,
      url: `${apiBaseUrl}/health`,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      cwd: path.resolve(repositoryRoot, "apps", "web"),
      env: { VITE_API_BASE_URL: apiBaseUrl },
      reuseExistingServer: false,
      timeout: 120_000,
      url: "http://127.0.0.1:5173/",
    },
  ],
});
