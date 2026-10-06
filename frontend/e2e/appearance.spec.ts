import { expect, test, type Page } from "@playwright/test";
import fixtures from "./fixtures/appearance.json" with { type: "json" };
import { mkdir } from "node:fs/promises";
// Deterministic local fixtures; real account data never enters review artifacts.
test.use({ serviceWorkers: "block" });
async function mockCompletedMember(page: Page) {
  await page.route("**/api/**", (route) => route.fulfill({
    status: 404,
    contentType: "application/json",
    body: JSON.stringify({ detail: "Not available in the browser fixture" }),
  }));
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      id: "018f0000-0000-7000-8000-000000000001",
      email: "member@example.com",
      phone_number: null,
      created_at: "2026-07-24T00:00:00Z",
      is_admin: false,
    }),
  }));
  await page.route("**/api/v1/profile/status", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      user_id: "018f0000-0000-7000-8000-000000000001",
      product_mode: "both",
      completion_state: "both_ready",
    }),
  }));
  await page.route("**/api/v1/profile", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      user_id: "018f0000-0000-7000-8000-000000000001",
      display_name: "Fitician member",
      birth_date: "2000-05-14",
      sex: "male",
      height_cm: 178,
      current_weight_kg: 76.5,
      shoulder_circumference_cm: null,
      waist_circumference_cm: null,
      hip_circumference_cm: null,
      fitness_goal: "build_muscle",
      experience_level: "beginner",
      training_days_per_week: 3,
      training_location: "gym",
      home_training_setup: null,
      session_duration_minutes: 60,
      training_cautions: [],
      plan_duration_weeks: 4,
      physical_limitations: null,
      weight_measured_at: "2026-07-27T10:30:00Z",
      circumferences_measured_at: null,
      created_at: "2026-07-27T10:30:00Z",
      updated_at: "2026-07-27T10:30:00Z",
    }),
  }));
}

for (const theme of ["dark", "light"] as const) {
  for (const viewport of [{ name: "phone", width: 390, height: 844 }, { name: "desktop", width: 1440, height: 1000 }]) {
    test(`${theme} authenticated surfaces on ${viewport.name}`, async ({ page }, testInfo) => {
      await page.setViewportSize(viewport);
      await page.addInitScript(value => { if (!localStorage.getItem("fitician.theme")) localStorage.setItem("fitician.theme", value); }, theme);
      await mockCompletedMember(page);
      await page.route("**/api/v1/entitlements/me", route => route.fulfill({ status: 200, json: {
        primary_package: "complete_care", active_packages: ["complete_care"], trial: { active: false, ends_at: null }, grants: [],
        entitlements: { granted: ["training.plan.generate", "nutrition.plan.generate", "body_analysis.run"], quotas: [] },
      }}));
      await page.route("**/api/v1/workout-plans/active", route => route.fulfill({ status: 200, json: fixtures.plan }));
      await page.route("**/api/v1/nutrition/estimates/current", route => route.fulfill({ status: 200, json: fixtures.nutrition }));
      await page.route("**/api/v1/progress/overview**", route => route.fulfill({ status: 200, json: fixtures.progress }));
      await page.route("**/api/v1/exercise-categories", route => route.fulfill({ status: 200, json: fixtures.categories }));
      await page.route("**/api/v1/exercises?**", route => route.fulfill({ status: 200, json: {
        items: [fixtures.exercise], total: 1, page: 1, page_size: 20, total_pages: 1,
      }}));
      await page.route("**/api/v1/exercises/dumbbell-bench-press**", route => route.fulfill({ status: 200, json: fixtures.exercise }));
      await page.route("**/api/v1/billing/offers", route => route.fulfill({ status: 200, json:
        ["training", "nutrition", "complete_care"].flatMap(package_code => [4, 6, 8].map(duration_weeks => ({
          offer_code: `${package_code}_${duration_weeks}w`, package_code, duration_weeks, price_irr: duration_weeks * 100000,
          currency: "IRR", is_available: true, entitlements: [], quota_policies: [],
        }))),
      }));
      await page.route("**/api/v1/program-conversations/workout/review**", route => route.fulfill({ status: 200, json: {
        available: true, review_id: "review", viewer_id: "member", unread_count: 0, older_cursor: null,
        messages: [{ id: "message", sender_id: "coach", body: "برنامه تمرین آماده است. سؤال‌هایت را اینجا بپرس.", created_at: "2026-10-01T10:00:00Z" }],
      }}));
      await mkdir("artifacts/appearance", { recursive: true });
      const errors: string[] = []; page.on("pageerror", error => errors.push(error.message));
      for (const route of ["dashboard", "workout-plan", "nutrition-estimate", "progress", "more", "profile", "exercises", "exercises/dumbbell-bench-press", "body-progress", "body-progress/new", "plans", "support", "support/new", "notifications", "conversation/workout/review"]) {
        await page.goto(`/${route}`, { waitUntil: "networkidle" });
        await expect(route === "body-progress/new" ? page.getByRole("region", { name: "اندازه‌های فعلی‌ات را تأیید کن" }) : page.locator("main").first()).toBeVisible();
        await expect(page.locator("html")).toHaveAttribute("data-fitician-theme", theme);
        expect(await page.evaluate(() => getComputedStyle(document.documentElement).colorScheme)).toBe(theme);
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
        await page.screenshot({ path: `artifacts/appearance/${testInfo.project.name}-${theme}-${viewport.name}-${route.replaceAll("/", "-")}.png`, fullPage: true });
      }
      expect(errors).toEqual([]);
      await page.goto("/more");
      await page.getByRole("radio", { name: theme === "dark" ? "روشن" : "تیره", exact: true }).check();
      const next = theme === "dark" ? "light" : "dark";
      await expect(page.locator("html")).toHaveAttribute("data-fitician-theme", next);
      await page.reload();
      await expect(page.locator("html")).toHaveAttribute("data-fitician-theme", next);
    });
  }
}
test("saved Light is applied before React loads", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fitician.theme", "light"));
  await page.route("**/assets/*.js", route => route.abort());
  await page.goto("/more", { waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("data-fitician-theme", "light");
  expect(await page.evaluate(() => document.documentElement.style.backgroundColor)).toBe("rgb(245, 250, 248)");
});

for (const theme of ["dark", "light"] as const) {
  test(`keeps Aqua avatar content readable in ${theme}`, async ({ page }) => {
    await page.addInitScript(value => localStorage.setItem("fitician.theme", value), theme);
    await mockCompletedMember(page);
    await page.goto("/more", { waitUntil: "networkidle" });
    await expect(page.locator(".more-profile-card__avatar")).toHaveCSS("color", "rgb(2, 6, 7)");
  });
}
