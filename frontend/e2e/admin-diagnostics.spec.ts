import { execFileSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

test.use({ serviceWorkers: "block", trace: "off" });

for (const language of ["fa", "en"] as const) {
    test(`persisted diagnostics ${language}`, async ({ page }, testInfo) => {
      test.setTimeout(60_000);
      const origin = new URL(testInfo.project.use.baseURL as string ?? "http://127.0.0.1:4173").origin;
      const email = `diagnostics-${randomUUID()}@example.com`;
      const password = `${randomUUID()}!aA9`;
      const created = await page.request.post("/api/v1/auth/register", { headers: { Origin: origin }, data: { email, password } });
      expect(created.status()).toBe(201);
      execFileSync("uv", ["run", "python", "-m", "scripts.e2e_fixture", "prepare-user", "--email", email, "--admin"], {
        cwd: resolve(process.cwd(), "../backend"), stdio: "pipe",
        env: { ...process.env, E2E_DATABASE_URL: process.env.E2E_DATABASE_URL ?? "postgresql+psycopg://fitician:fitician@127.0.0.1:5544/diagnostics_e2e" },
      });
      const correlation = randomUUID();
      const event = { platform: "web", component: "WebTransport", operation: "workout_generation", stage: "response_failed", error_code: "API_REQUEST_FAILED", request_id: correlation, http_status: 503 };
      const intake = await page.request.post("/api/v1/diagnostics/client", { headers: { Origin: origin }, data: { events: Array.from({length: 5}, () => ({...event, event_id: randomUUID()})) } });
      expect(intake.status()).toBe(202);
      const issues = await (await page.request.get(`/api/v1/admin/diagnostics/issues?request_id=${correlation}`)).json();
      expect(issues).toHaveLength(1);
      const issueId = issues[0].id as string;
      const alerts = await (await page.request.get("/api/v1/admin/diagnostics/alerts")).json();
      expect(alerts.some((row: { issue_id: string }) => row.issue_id === issueId)).toBe(true);
      await page.addInitScript((lang) => localStorage.setItem("fitician-language", lang), language);
      await page.setViewportSize({width: 390, height: 1000});
      await page.goto("/admin/diagnostics");
      await expect(page.getByRole("heading", {name: language === "fa" ? "لاگینگ و دیباگینگ" : "Logging & Debugging", exact: true})).toBeVisible();
      await expect(page.getByRole("img", {name: /روند|Operation trend/})).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
      await page.screenshot({path: testInfo.outputPath("overview-390.png"), fullPage: true});
      await page.setViewportSize({width: 1440, height: 1000});
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
      await page.screenshot({path: testInfo.outputPath("overview-1440.png"), fullPage: true});
      await page.goto(`/admin/diagnostics?tab=issues&issue=${issueId}`);
      await expect(page.getByText("API_REQUEST_FAILED", {exact: true}).first()).toBeVisible();
      const status = page.getByRole("combobox", {name: language === "fa" ? "وضعیت" : "Status", exact: true});
      await status.selectOption("investigating");
      await page.getByRole("button", {name: language === "fa" ? "ثبت" : "Save", exact: true}).click();
      await expect.poll(async () => (await (await page.request.get(`/api/v1/admin/diagnostics/issues/${issueId}`)).json()).issue.status).toBe("investigating");
      await page.goto(`/admin/diagnostics?tab=events&request_id=${correlation}`);
      await expect(page.locator(".diagnostics-table tbody tr")).toHaveCount(5);
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
      await page.screenshot({path: testInfo.outputPath("timeline-1440.png"), fullPage: true});
      await page.setViewportSize({width: 390, height: 1000});
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 1)).toBe(true);
      await page.screenshot({path: testInfo.outputPath("timeline-390.png"), fullPage: true});
    });
}
