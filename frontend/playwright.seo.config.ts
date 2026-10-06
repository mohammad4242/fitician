import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./seo-e2e", fullyParallel: true, workers: 2,
  use: { baseURL: process.env.PLAYWRIGHT_SEO_BASE_URL ?? "http://127.0.0.1:4180", trace: "retain-on-failure", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["iPhone 13"], defaultBrowserType: "chromium" } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
