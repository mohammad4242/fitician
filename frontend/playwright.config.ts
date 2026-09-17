import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig, devices } from "@playwright/test";

const frontendDirectory = dirname(fileURLToPath(import.meta.url));
const backendDirectory = resolve(frontendDirectory, "../backend");
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173";
const e2eDatabaseUrl = process.env.E2E_DATABASE_URL
  ?? "postgresql+psycopg://fitician:fitician@127.0.0.1:5432/fitician_e2e";
const backendEnvironment = {
  ...process.env,
  APP_ENV: "test",
  COOKIE_SECURE: "false",
  DATABASE_URL: e2eDatabaseUrl,
  E2E_DATABASE_URL: e2eDatabaseUrl,
  FRONTEND_ORIGIN: baseURL,
  FRONTEND_ORIGINS: "http://localhost:4173",
  SESSION_COOKIE_NAME: "fitician_session",
  BILLING_DEFAULT_PROVIDER: "fake",
  BILLING_FAKE_PROVIDER_ENABLED: "true",
};

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 2 : 0,
  reporter: process.env.CI ? "github" : "list",
  use: {
    baseURL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: [
    {
      command: "uv run python -m scripts.e2e_prepare && uv run python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
      cwd: backendDirectory,
      env: backendEnvironment,
      url: "http://127.0.0.1:8000/openapi.json",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4173",
      cwd: frontendDirectory,
      env: {
        ...process.env,
        VITE_API_PROXY_TARGET: "http://127.0.0.1:8000",
      },
      url: `${baseURL}/`,
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
