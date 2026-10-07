import { expect, test, type Page } from "@playwright/test";

test.use({ serviceWorkers: "block" });
const userId = "018f0000-0000-7000-8000-000000000001";
const timestamp = "2026-10-07T18:00:15Z";
const member = { user_id: userId, display_name: "عضو نمونه / Sample member", email: `${"long-address-".repeat(7)}@example.com`, phone_number: "+989123456789", created_at: timestamp, primary_package: "complete", active_packages: ["complete"], trial_active: false, trial_ends_at: null, paid_access_end: timestamp, last_activity_at: timestamp, usage_status: "active" };
const pageOf = (items: unknown[]) => ({ items, total: items.length, limit: 25, offset: 0 });
const workout = { id: "workout-1", created_at: timestamp, activated_at: timestamp, status: "active", primary_goal: "hypertrophy", secondary_goal: null, duration_weeks: 6, training_days: 4, review_status: "coach_approved", days: [{ day_number: 1, title_en: "Upper body", title_fa: "بالاتنه", estimated_duration_minutes: 40, exercises: [{ name_en: "Push-up", name_fa: "شنا", sets: 3, reps_min: 8, reps_max: 12, duration_min_seconds: null, duration_max_seconds: null, rest_seconds: 60 }] }] };
const nutrition = { id: "nutrition-1", revision: 2, lifecycle_status: "active", review_status: "approved", created_at: timestamp, start_date: "2026-10-07", started_at: timestamp, budget_status: "within_budget", selected: true, is_user_visible: true, plan_role: "budget", days: [{ day_index: 0, plan_date: "2026-10-07", meals: [{ slot: "main_meal", foods: [{ name_en: "Bread", name_fa: "نان", grams: 60 }] }] }] };

async function mockAdmin(page: Page) {
  await page.route("**/api/**", async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname;
    let data: unknown = [];
    if (path === "/api/v1/auth/me") data = { id: userId, email: "admin-fixture@example.com", is_admin: true, created_at: timestamp };
    else if (path === "/api/v1/profile/status") data = { user_id: userId, product_mode: "training", completion_state: "training_ready" };
    else if (path === "/api/v1/entitlements/me") data = { primary_package: "complete", active_packages: ["complete"], trial: { active: false, ends_at: null }, grants: [], entitlements: { granted: [], quotas: [] } };
    else if (path.endsWith("/access/overview")) data = { timezone: "Asia/Tehran", generated_at: timestamp, today_start: timestamp, week_start: timestamp, month_start: timestamp, total_users: 1431, registrations_today: 12, registrations_week: 47, registrations_month: 82, active_users_24h: 25, active_users_7d: 78, active_users_30d: 194, active_paid_users: 40, purchases_today: 3, purchases_week: 8, purchases_month: 21, workout_plans: 321, nutrition_plans: 177, body_analyses_completed: 88, daily_signups: Array.from({ length: 30 }, (_, i) => ({ date: new Date(Date.UTC(2026, 8, 8 + i)).toISOString().slice(0, 10), count: i % 7 })), recent_users: [member] };
    else if (path.endsWith("/access/users")) data = { items: [{ ...member, display_name: url.searchParams.has("offset") ? "Page two member" : member.display_name }], total: url.searchParams.has("q") ? 1 : 26, limit: 25, offset: Number(url.searchParams.get("offset") ?? 0) };
    else if (path.endsWith("/insights")) data = { last_activity_at: timestamp, login_count: 12, legacy_login_evidence_count: 3, workout_plans: 4, nutrition_plans: 2, completed_workout_sessions: 17, skipped_workout_sessions: 1, weekly_checkins: 2, body_analyses: 2, body_analyses_completed: 2, latest_weight_kg: 81.4 };
    else if (path.endsWith("/activity")) data = pageOf(Array.from({ length: 25 }, (_, i) => ({ id: `event-${i}`, event_type: i % 2 ? "workout.plan_generated" : "auth.login_succeeded", resource_type: "safe_resource", resource_id: `resource-${i}`, metadata: i % 2 ? { primary_goal: "hypertrophy", training_days: 4 } : { platform: "android", auth_method: "google", device_name: "Pixel" }, occurred_at: timestamp, source: "explicit" })));
    else if (path.endsWith("/logins")) data = pageOf([{ id: "login-1", occurred_at: timestamp, platform: "android", auth_method: "google", app_version: "1.2.3", device_name: "Pixel", evidence: "explicit_login" }, { id: "legacy-login", occurred_at: timestamp, platform: "web", auth_method: null, device_name: null, app_version: null, evidence: "legacy_web_session" }]);
    else if (path.endsWith("/workout-plans")) data = pageOf([workout]);
    else if (path.endsWith("/workout-plans/workout-1")) data = workout;
    else if (path.endsWith("/nutrition-plans")) data = pageOf([nutrition]);
    else if (path.endsWith("/nutrition-plans/nutrition-1")) data = nutrition;
    else if (path.endsWith("/progress")) data = pageOf([{ id: "measurement", measured_at: timestamp, weight_kg: 81.4, waist_circumference_cm: 80, hip_circumference_cm: null, shoulder_circumference_cm: null, shoulder_width_cm: null, observed_fields: ["weight_kg", "waist_circumference_cm"] }]);
    else if (path.endsWith("/body-analyses")) data = pageOf([{ id: "analysis-1", created_at: timestamp, completed_at: timestamp, status: "review_pending", revision: 1 }]);
    else if (path.endsWith(`/access/users/${userId}`)) data = { member, entitlement_snapshot: { primary_package: "complete", active_packages: ["complete"], granted_entitlements: [], trial_active: false, trial_ends_at: null }, grants: [{ id: "018f0000-0000-7000-8000-000000000003", package_code: "complete", source: "subscription", term_weeks: 6, starts_at: timestamp, ends_at: timestamp, revoked_at: null, created_at: timestamp, status: "active", is_currently_active: true, billing_order_id: "order-1", campaign_id: null, campaign_name: null }] };
    await route.fulfill({ status: 200, json: data });
  });
}

for (const language of ["fa", "en"] as const) {
  for (const theme of ["dark", "light"] as const) {
    for (const width of [320, 768, 1440]) {
      test(`${language} ${theme} ${width}px Admin overview and User 360`, async ({ page }, testInfo) => {
        await page.setViewportSize({ width, height: 1000 });
        await page.addInitScript(({ language, theme }) => { localStorage.setItem("fitician-language", language); localStorage.setItem("fitician.theme", theme); }, { language, theme });
        const errors: string[] = [];
        page.on("pageerror", (error) => errors.push(error.message));
        await mockAdmin(page);
        const noOverflow = async () => expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
        await page.goto("/admin/billing/overview");
        await expect(page.getByRole("heading", { name: language === "fa" ? "ثبت‌نام و رشد" : "Registration & growth" })).toBeVisible();
        await expect(page.locator("html")).toHaveAttribute("dir", language === "fa" ? "rtl" : "ltr");
        await noOverflow();
        await page.screenshot({ path: testInfo.outputPath("overview.png"), fullPage: true });
        await page.goto("/admin/billing/users");
        await expect(page.locator(".access-user-card")).toHaveCount(1);
        await noOverflow();
        await page.getByRole("button", { name: language === "fa" ? "بعدی" : "Next", exact: true }).click();
        await expect(page.getByRole("heading", { name: "Page two member" })).toBeVisible();
        await page.getByRole("searchbox").fill("member");
        await page.getByRole("button", { name: language === "fa" ? "جست‌وجو" : "Search", exact: true }).click();
        await expect(page).toHaveURL(/q=member/);
        await page.screenshot({ path: testInfo.outputPath("users.png"), fullPage: true });
        await page.goto(`/admin/billing/users/${userId}`);
        await expect(page.locator(".access-activity-marker")).toHaveCount(25);
        await expect(page.locator(".access-user360__timeline")).not.toContainText("auth.login_succeeded");
        await noOverflow();
        await page.screenshot({ path: testInfo.outputPath("activity.png"), fullPage: true });
        for (const tab of ["logins", "plans", "progress", "accessTab", "billingTab"] as const) {
          const labels = { fa: { logins: "تاریخچه ورود", plans: "برنامه‌ها", progress: "پیشرفت", accessTab: "دسترسی", billingTab: "صورتحساب" }, en: { logins: "Login history", plans: "Plans", progress: "Progress", accessTab: "Access", billingTab: "Billing" } };
          await page.getByRole("button", { name: labels[language][tab], exact: true }).click();
          await expect(page.locator(".access-user360 [role=status]")).toHaveCount(0);
          if (tab === "plans") {
            await page.locator(".access-plan-disclosure > summary").first().click();
            await expect(page.locator(".access-user360__detail")).toBeVisible();
          }
          await noOverflow();
          await page.screenshot({ path: testInfo.outputPath(`${tab}.png`), fullPage: true });
        }
        expect(errors).toEqual([]);
      });
    }
  }
}
