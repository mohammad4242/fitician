import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "ios-pwa-welcome.spec.ts",
  outputDir: "./test-results/ios-pwa-welcome",
  workers: 2,
  use: { baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:4199", serviceWorkers: "block" },
  projects: [{ name: "webkit", use: { ...devices["iPhone 13"] } }],
  webServer: process.env.PLAYWRIGHT_BASE_URL ? undefined : {
    command: "npm run preview -- --host 127.0.0.1 --port 4199",
    url: "http://127.0.0.1:4199", reuseExistingServer: false,
  },
});
