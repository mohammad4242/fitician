import { expect, test, type Page } from "@playwright/test";
// API fixtures must remain visible to routing after public-page service worker registration.
test.use({ serviceWorkers: "block" });

async function mockCompletedMember(page: Page) {
  await page.route("**/api/**", (route) =>
    route.fulfill({
      status: 404,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Not available in the browser fixture" }),
    }),
  );
  await page.route("**/api/v1/auth/me", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "018f0000-0000-7000-8000-000000000001",
        email: "member@example.com",
        phone_number: null,
        created_at: "2026-07-24T00:00:00Z",
        is_admin: false,
      }),
    }),
  );
  await page.route("**/api/v1/profile/status", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        user_id: "018f0000-0000-7000-8000-000000000001",
        product_mode: "training",
        completion_state: "training_ready",
      }),
    }),
  );
  await page.route("**/api/v1/profile", (route) =>
    route.fulfill({
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
    }),
  );
}

const empty = {
  unit: "cm",
  points: [],
  start_value: null,
  latest_value: null,
  delta: null,
};
for (const language of ["fa", "en"]) {
  for (const width of [320, 1440]) {
    test(`Support and Progress ${language} at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 900 });
      await page.addInitScript(
        (lang) => localStorage.setItem("fitician-language", lang),
        language,
      );
      await page.route("**/api/v1/auth/me", (route) =>
        route.fulfill({ status: 401, body: "{}" }),
      );
      await page.goto("/support");
      await expect(
        page.getByRole("heading", {
          name:
            language === "fa" ? "چطور می‌تونیم کمکت کنیم؟" : "How can we help?",
        }),
      ).toBeVisible();
      await expect(
        page.getByRole("link", { name: "fitician.fit@gmail.com" }),
      ).toHaveAttribute("href", "mailto:fitician.fit@gmail.com");
      await expect(page.locator("html")).toHaveAttribute(
        "dir",
        language === "fa" ? "rtl" : "ltr",
      );
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      await mockCompletedMember(page);
      await page.route("**/api/v1/progress/overview**", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            context: {
              preset: "week",
              timezone: "Asia/Tehran",
              today: "2026-10-02",
              start_date: "2026-09-26",
              end_date: "2026-10-02",
              training_enabled: true,
              nutrition_enabled: true,
              goal: "build_muscle",
              week_number: 1,
            },
            training: {
              planned_sessions: 4,
              due_sessions: 4,
              completed_sessions: 3,
              skipped_sessions: 1,
              overdue_sessions: 0,
              adherence_percent: 75,
              weeks: [{ start_date: "2026-09-26", planned: 4, completed: 3 }],
            },
            nutrition: {
              series: [
                { date: "2026-09-26", target_kcal: 2200, actual_kcal: 2140 },
                {
                  date: "2026-09-27",
                  target_kcal: 2200,
                  actual_kcal: null,
                  logging_state: "missing",
                },
                { date: "2026-09-28", target_kcal: 2000, actual_kcal: 2180 },
              ],
              logged_days: 2,
              elapsed_days: 6,
              comparable_days: 2,
              adherent_days: 2,
              average_difference_kcal: 60,
            },
            body_measurements: {
              weight: {
                unit: "kg",
                points: [
                  {
                    recorded_at: "2026-09-26T12:00:00Z",
                    value: 80,
                    source: "manual",
                  },
                  {
                    recorded_at: "2026-10-01T12:00:00Z",
                    value: 79,
                    source: "manual",
                  },
                ],
                start_value: 80,
                latest_value: 79,
                delta: -1,
              },
              waist: empty,
              hip: empty,
              shoulder_width: empty,
            },
            recovery: [
              {
                recorded_at: "2026-10-01T12:00:00Z",
                week_number: 1,
                recovery: "good",
                difficulty: "appropriate",
              },
            ],
            body_analysis: {},
            insights: [],
          }),
        }),
      );
      await page.goto("/progress");
      await expect(
        page.getByRole("heading", {
          name: language === "fa" ? "پیشرفت من" : "My Progress",
          exact: true,
        }),
      ).toBeVisible();
      await expect(page.locator(".progress-chart")).toHaveCount(2);
      await expect
        .poll(() =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= innerWidth,
          ),
        )
        .toBe(true);
      await page.screenshot({
        path: `test-results/progress-${language}-${width}.png`,
        fullPage: true,
      });
    });
  }
}
