import { defineConfig, devices } from "@playwright/test";

// Public install checks need only the prerendered frontend, with no test database.
export default defineConfig({
  testDir: "./e2e",
  testMatch: "install.spec.ts",
  workers: 2,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4173", screenshot: "only-on-failure" },
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 4173",
    url: "http://127.0.0.1:4173/install",
    reuseExistingServer: false,
  },
});
