import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const accessApi = vi.hoisted(() => ({
  adminAccessPackageCodes: ["training", "training_coach", "complete", "complete_care"],
  getCampaigns: vi.fn(),
  getUserAccess: vi.fn(),
  getUserInsights: vi.fn(), getUserActivity: vi.fn(), getUserLogins: vi.fn(), getWorkoutPlans: vi.fn(), getWorkoutPlan: vi.fn(), getNutritionPlans: vi.fn(), getNutritionPlan: vi.fn(), getUserProgress: vi.fn(), getUserBodyAnalyses: vi.fn(),
  grantUserAccess: vi.fn(),
  redeemUserCampaign: vi.fn(),
  revokeUserAccess: vi.fn(),
}));
vi.mock("./adminAccessApi", () => accessApi);

import { AdminUserAccessDetailPage } from "./AdminUserAccessDetailPage";
import { AdminUser360Sections } from "./AdminUser360Sections";

const access = {
  member: {
    user_id: "member-1",
    display_name: "علی رضایی",
    email: "ali@example.com",
    phone_number: null,
    created_at: "2026-09-13T08:00:00Z",
    primary_package: "complete" as const,
    active_packages: ["complete"] as const,
    trial_active: false,
    trial_ends_at: null,
    paid_access_end: "2026-11-13T08:00:00Z",
  },
  entitlement_snapshot: {
    primary_package: "complete" as const,
    active_packages: ["complete"] as const,
    granted_entitlements: ["training.plan.generate", "body_analysis.run"] as const,
    trial_active: false,
    trial_ends_at: null,
  },
  grants: [
    {
      id: "subscription-grant",
      package_code: "complete" as const,
      source: "subscription" as const,
      term_weeks: 8 as const,
      starts_at: "2026-09-13T08:00:00Z",
      ends_at: "2026-11-13T08:00:00Z",
      revoked_at: null,
      created_at: "2026-09-13T08:00:00Z",
      status: "active" as const,
      is_currently_active: true,
      billing_order_id: "order-1",
      campaign_id: null,
      campaign_name: null,
    },
    {
      id: "revoked-grant",
      package_code: "training_coach" as const,
      source: "admin" as const,
      term_weeks: 4 as const,
      starts_at: "2026-08-01T08:00:00Z",
      ends_at: "2026-09-01T08:00:00Z",
      revoked_at: "2026-08-20T08:00:00Z",
      created_at: "2026-08-01T08:00:00Z",
      status: "revoked" as const,
      is_currently_active: false,
      billing_order_id: null,
      campaign_id: null,
      campaign_name: null,
    },
  ],
};

const campaign = {
  id: "campaign-1",
  code: "beta-promotion",
  name: "Beta promotion",
  description: null,
  kind: "manual_promotion" as const,
  package_code: "training_coach" as const,
  duration_days: 30,
  term_weeks: 4 as const,
  available_from: null,
  available_until: null,
  is_active: true,
  max_total_redemptions: null,
  redemption_count: 0,
  created_by_user_id: null,
  created_at: "2026-09-13T08:00:00Z",
  updated_at: "2026-09-13T08:00:00Z",
};
const signupBonusCampaign = {
  ...campaign,
  id: "campaign-signup-bonus",
  code: "signup-bonus",
  name: "Signup Bonus",
  kind: "signup_bonus" as const,
};

beforeEach(() => {
  for (const method of [accessApi.getUserActivity, accessApi.getUserLogins, accessApi.getWorkoutPlans, accessApi.getWorkoutPlan, accessApi.getNutritionPlans, accessApi.getNutritionPlan, accessApi.getUserProgress, accessApi.getUserBodyAnalyses]) method.mockReset();
  accessApi.getUserAccess.mockReset();
  accessApi.getCampaigns.mockReset();
  accessApi.grantUserAccess.mockReset();
  accessApi.redeemUserCampaign.mockReset();
  accessApi.revokeUserAccess.mockReset();
  accessApi.getUserAccess.mockResolvedValue(access);
  accessApi.getUserInsights.mockResolvedValue({ last_activity_at: null, login_count: 0, legacy_login_evidence_count: 0, workout_plans: 0, nutrition_plans: 0, completed_workout_sessions: 0, skipped_workout_sessions: 0, weekly_checkins: 0, body_analyses: 0, body_analyses_completed: 0, latest_weight_kg: null });
  for (const method of [accessApi.getUserActivity, accessApi.getUserLogins, accessApi.getWorkoutPlans, accessApi.getNutritionPlans, accessApi.getUserProgress, accessApi.getUserBodyAnalyses]) method.mockResolvedValue({ items: [], total: 0, limit: 25, offset: 0 });
  accessApi.getWorkoutPlan.mockResolvedValue({ id: "workout-1", created_at: "2026-10-01T08:00:00Z", activated_at: null, status: "active", primary_goal: "hypertrophy", secondary_goal: null, duration_weeks: 4, training_days: 4, review_status: "approved", days: [{ day_number: 1, title_en: "Upper body", title_fa: "بالاتنه", estimated_duration_minutes: 40, exercises: [{ name_en: "Push-up", name_fa: "شنا", sets: 3, reps_min: 8, reps_max: 12, duration_min_seconds: null, duration_max_seconds: null, rest_seconds: 60 }] }] });
  accessApi.getNutritionPlan.mockResolvedValue({ id: "nutrition-1", revision: 1, lifecycle_status: "active", review_status: "approved", created_at: "2026-10-01T08:00:00Z", start_date: "2026-10-02", started_at: null, budget_status: "within_budget", selected: true, is_user_visible: true, plan_role: "primary", days: [{ day_index: 0, plan_date: "2026-10-02", meals: [{ slot: "breakfast", foods: [{ name_fa: "نان", name_en: "Bread", grams: 60 }] }] }] });
  accessApi.getCampaigns.mockResolvedValue([campaign, signupBonusCampaign]);
  accessApi.grantUserAccess.mockResolvedValue(access.grants[0]);
  accessApi.redeemUserCampaign.mockResolvedValue({ campaign, grant: access.grants[1] });
  accessApi.revokeUserAccess.mockResolvedValue({ ...access.grants[0], status: "revoked" });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={["/admin/billing/users/member-1"]}>
      <Routes>
        <Route path="/admin/billing/users/:userId" element={<AdminUserAccessDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

it("shows identity, entitlement snapshot, and clearly labeled grant history", async () => {
  renderDetail();

  expect(await screen.findByRole("heading", { name: "علی رضایی" })).toBeInTheDocument();
  expect(screen.getByText("خلاصه دسترسی‌ها")).toBeInTheDocument();
  expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  expect(screen.getByText("REVOKED")).toBeInTheDocument();
  expect(screen.getByText("اشتراک")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox", { name: /training\.plan|body_analysis/ })).not.toBeInTheDocument();
});

it("shows the User 360 summary and independently loaded activity and login sections", async () => {
  renderDetail();
  expect(await screen.findByRole("heading", { name: "خلاصه تعامل" })).toBeInTheDocument();
  expect(screen.getByText("ورودهای موفق")).toBeInTheDocument();
  expect(await screen.findByRole("heading", { name: "فعالیت‌ها" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "تاریخچه ورود" })).toBeInTheDocument();
  expect(screen.getByText(/تعداد ورود موفق فقط شامل رویدادهای صریح ورود/)).toBeInTheDocument();
  expect(screen.getAllByText("موردی ثبت نشده است.").length).toBeGreaterThan(0);
});

it("renders historical session context and localized explicit login metadata", async () => {
  accessApi.getUserActivity.mockResolvedValue({
    items: [{ id: "event-1", event_type: "workout.session_completed", resource_type: "workout_session", resource_id: "session-1", metadata: { week_number: 2, session_number: 1 }, occurred_at: "2026-10-01T18:00:00Z", source: "historical" }],
    total: 1, limit: 25, offset: 0,
  });
  accessApi.getUserLogins.mockResolvedValue({
    items: [{ id: "login-1", occurred_at: "2026-10-01T17:00:00Z", platform: "android", auth_method: "google", app_version: "1.2.0", device_name: "Pixel", evidence: "explicit_login" }],
    total: 1, limit: 25, offset: 0,
  });
  renderDetail();

  expect(await screen.findByText("ورود به حساب")).toBeInTheDocument();
  expect(screen.getByText(/هفته: 2 · جلسه: 1/)).toBeInTheDocument();
  expect(screen.getByText(/اندروید · گوگل · Pixel · نسخه برنامه: 1.2.0/)).toBeInTheDocument();
});

it("loads workout, nutrition, progress, and safe body analysis sections from their tabs", async () => {
  const user = userEvent.setup();
  accessApi.getUserProgress.mockResolvedValue({
    items: [
      { id: "measurement-1", measured_at: "2026-10-01T08:00:00Z", weight_kg: 81.4, waist_circumference_cm: 80, hip_circumference_cm: null, shoulder_circumference_cm: null, shoulder_width_cm: null, observed_fields: ["weight_kg", "waist_circumference_cm"] },
      { id: "measurement-2", measured_at: "2026-10-02T08:00:00Z", weight_kg: null, waist_circumference_cm: 79, hip_circumference_cm: null, shoulder_circumference_cm: null, shoulder_width_cm: null, observed_fields: ["waist_circumference_cm"] },
    ],
    total: 1, limit: 25, offset: 0,
  });
  accessApi.getUserBodyAnalyses.mockResolvedValue({
    items: [{ id: "analysis-1", created_at: "2026-10-01T08:00:00Z", completed_at: "2026-10-01T08:05:00Z", status: "completed", revision: 2 }],
    total: 1, limit: 25, offset: 0,
  });
  renderDetail();
  await screen.findByRole("heading", { name: "خلاصه تعامل" });
  await user.click(screen.getByRole("button", { name: "برنامه‌ها" }));
  expect(await screen.findByRole("heading", { name: "برنامه‌های تمرین" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "برنامه‌های تغذیه" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "پیشرفت" }));
  expect(await screen.findByRole("heading", { name: "پیشرفت" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "تحلیل‌های بدن" })).toBeInTheDocument();
  expect(await screen.findByText("وزن: 81.4 kg")).toBeInTheDocument();
  expect(await screen.findByText("اندازه‌گیری بدن")).toBeInTheDocument();
  expect(screen.getByText("تکمیل‌شده")).toBeInTheDocument();
});

it("opens safe workout and nutrition details only on demand", async () => {
  const user = userEvent.setup();
  let resolveWorkout!: (value: { id: string; created_at: string; activated_at: string | null; status: string; primary_goal: string; secondary_goal: string | null; duration_weeks: number; training_days: number; review_status: string; days: { day_number: number; title_en: string; title_fa: string; estimated_duration_minutes: number; exercises: { name_en: string; name_fa: string; sets: number; reps_min: number; reps_max: number; duration_min_seconds: null; duration_max_seconds: null; rest_seconds: number }[] }[] }) => void;
  const workoutDetail = { id: "workout-1", created_at: "2026-10-01T08:00:00Z", activated_at: null, status: "active", primary_goal: "hypertrophy", secondary_goal: null, duration_weeks: 4, training_days: 4, review_status: "approved", days: [{ day_number: 1, title_en: "Upper body", title_fa: "بالاتنه", estimated_duration_minutes: 40, exercises: [{ name_en: "Push-up", name_fa: "شنا", sets: 3, reps_min: 8, reps_max: 12, duration_min_seconds: null, duration_max_seconds: null, rest_seconds: 60 }] }] };
  accessApi.getWorkoutPlan.mockReturnValue(new Promise((resolve) => { resolveWorkout = resolve; }));
  accessApi.getWorkoutPlans.mockResolvedValue({ items: [{ id: "workout-1", created_at: "2026-10-01T08:00:00Z", activated_at: null, status: "active", primary_goal: "hypertrophy", secondary_goal: null, duration_weeks: 4, training_days: 4, review_status: "approved" }], total: 1, limit: 25, offset: 0 });
  accessApi.getNutritionPlans.mockResolvedValue({ items: [{ id: "nutrition-1", revision: 1, lifecycle_status: "active", review_status: "approved", created_at: "2026-10-01T08:00:00Z", start_date: "2026-10-02", started_at: null, budget_status: "within_budget", selected: true, is_user_visible: true, plan_role: "primary" }], total: 1, limit: 25, offset: 0 });
  renderDetail();
  await screen.findByRole("heading", { name: "خلاصه تعامل" });
  await user.click(screen.getByRole("button", { name: "برنامه‌ها" }));
  await screen.findByRole("heading", { name: "برنامه‌های تمرین" });
  expect(accessApi.getWorkoutPlan).not.toHaveBeenCalled();
  await user.click(screen.getAllByText("جزئیات")[0]);
  expect(await screen.findByRole("status")).toHaveTextContent("در حال دریافت اطلاعات دسترسی");
  resolveWorkout(workoutDetail);
  expect(await screen.findByText(/شنا · 3 × 8–12/)).toBeInTheDocument();
  accessApi.getNutritionPlan.mockRejectedValueOnce(new Error("offline"));
  await user.click(screen.getAllByText("جزئیات")[1]);
  expect(await screen.findByRole("alert")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "تلاش دوباره" }));
  expect(await screen.findByText(/صبحانه: نان \(60g\)/)).toBeInTheDocument();
  expect(accessApi.getNutritionPlan).toHaveBeenCalledWith("member-1", "nutrition-1");
});

it("shows a section error without breaking access controls", async () => {
  accessApi.getUserActivity.mockRejectedValueOnce(new Error("offline"));
  renderDetail();
  expect(await screen.findByRole("alert")).toHaveTextContent("اطلاعات دسترسی دریافت نشد.");
  expect(screen.getByRole("button", { name: "اعطای دسترسی" })).toBeInTheDocument();
});

it("drops old insights and section requests when the selected user changes", async () => {
  let resolveOld!: (value: typeof insights) => void;
  const insights = { last_activity_at: null, login_count: 1, legacy_login_evidence_count: 0, workout_plans: 0, nutrition_plans: 0, completed_workout_sessions: 0, skipped_workout_sessions: 0, weekly_checkins: 0, body_analyses: 0, body_analyses_completed: 0, latest_weight_kg: null };
  accessApi.getUserInsights.mockImplementation((id: string) => id === "old-user" ? new Promise((resolve) => { resolveOld = resolve; }) : Promise.resolve({ ...insights, login_count: 9 }));
  const { rerender } = render(<AdminUser360Sections userId="old-user" member={{ ...access.member, user_id: "old-user" }} />);
  rerender(<AdminUser360Sections userId="new-user" member={{ ...access.member, user_id: "new-user" }} />);
  expect(await screen.findByText("9")).toBeInTheDocument();
  resolveOld(insights);
  await waitFor(() => expect(screen.getByText("9")).toBeInTheDocument());
  expect(accessApi.getUserActivity).toHaveBeenLastCalledWith("new-user", { limit: 25, offset: 0 });
});

it("grants a package and applies a manual campaign with a reason", async () => {
  const user = userEvent.setup();
  renderDetail();

  await user.click(await screen.findByRole("button", { name: "اعطای دسترسی" }));
  expect(screen.queryByRole("option", { name: "دوره آزمایشی شروع" })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("بسته"), "training_coach");
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), "4");
  await user.click(screen.getByRole("button", { name: "پایان" }));
  await user.click(screen.getByRole("button", { name: "انتخاب" }));
  await user.type(screen.getByLabelText("دلیل"), "beta tester");
  expect(screen.queryByLabelText("کلید درخواست")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.grantUserAccess).toHaveBeenCalledWith("member-1", expect.objectContaining({
    package_code: "training_coach",
    term_weeks: 4,
    ends_at: expect.any(String),
    reason: "beta tester",
    client_idempotency_key: expect.any(String),
  }));

  await user.click(screen.getByRole("button", { name: "اعمال کمپین" }));
  expect(screen.queryByRole("option", { name: "Signup Bonus" })).not.toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Beta promotion" })).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("کمپین را انتخاب کنید"), "campaign-1");
  await user.type(screen.getByLabelText("دلیل اعمال کمپین"), "manual beta access");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.redeemUserCampaign).toHaveBeenCalledWith(
    "member-1",
    "campaign-1",
    "manual beta access",
  );
});

it("generates one hidden grant idempotency key and reuses it for retries", async () => {
  const user = userEvent.setup();
  const randomUUID = vi.fn().mockReturnValue("generated-grant-key");
  vi.stubGlobal("crypto", { randomUUID });
  accessApi.grantUserAccess
    .mockRejectedValueOnce(new Error("retry"))
    .mockResolvedValueOnce(access.grants[0]);
  renderDetail();

  await user.click(await screen.findByRole("button", { name: "اعطای دسترسی" }));
  await user.click(screen.getByRole("button", { name: "پایان" }));
  await user.click(screen.getByRole("button", { name: "انتخاب" }));
  await user.type(screen.getByLabelText("دلیل"), "retryable support action");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  const calls = accessApi.grantUserAccess.mock.calls;
  expect(randomUUID).toHaveBeenCalledTimes(1);
  expect(calls).toHaveLength(2);
  expect(calls[0][1].client_idempotency_key).toBe("generated-grant-key");
  expect(calls[1][1].client_idempotency_key).toBe("generated-grant-key");
  expect(screen.queryByLabelText("کلید درخواست")).not.toBeInTheDocument();
});

it("warns before revoking paid access and sends a mandatory reason", async () => {
  const user = userEvent.setup();
  renderDetail();

  const grant = await screen.findByTestId("access-grant-subscription-grant");
  await user.click(within(grant).getByRole("button", { name: "قطع دسترسی" }));
  expect(screen.getByText("قطع دسترسی وضعیت مالی سفارش را Refund نمی‌کند.")).toBeInTheDocument();
  await user.type(screen.getByLabelText("دلیل قطع دسترسی"), "support correction");
  await user.click(screen.getByRole("button", { name: "تأیید قطع دسترسی" }));

  expect(accessApi.revokeUserAccess).toHaveBeenCalledWith("subscription-grant", "support correction");
});

it("shows login timestamps with seconds in Tehran time", async () => {
  accessApi.getUserLogins.mockResolvedValue({ items: [{ id: "login-seconds", occurred_at: "2026-10-01T08:00:15Z", platform: "web", auth_method: "password", app_version: null, device_name: null, evidence: "explicit_login" }], total: 1, limit: 25, offset: 0 });
  renderDetail();
  expect(await screen.findByText(/۱۱:۳۰:۱۵/)).toBeInTheDocument();
});


it("labels real nutrition and body analysis lifecycle states", async () => {
  accessApi.getNutritionPlans.mockResolvedValue({ items: [{ id: "nutrition-1", revision: 1, lifecycle_status: "pending_physician_review", review_status: "in_review", created_at: "2026-10-01T08:00:00Z", start_date: "2026-10-02", started_at: null, budget_status: "flexible_overage", selected: false, is_user_visible: false, plan_role: "primary" }], total: 1, limit: 25, offset: 0 });
  accessApi.getUserBodyAnalyses.mockResolvedValue({ items: [{ id: "analysis-1", created_at: "2026-10-01T08:00:00Z", completed_at: null, status: "review_pending", revision: 1 }], total: 1, limit: 25, offset: 0 });
  render(<MemoryRouter><AdminUser360Sections userId="member-1" member={access.member} /></MemoryRouter>);
  await userEvent.click(screen.getByRole("button", { name: "برنامه‌ها" }));
  expect(await screen.findByText(/در انتظار بررسی پزشک/)).toBeInTheDocument();
  expect(screen.getByText(/در حال بررسی/)).toBeInTheDocument();
  expect(screen.getByText(/افزایش مجاز بودجه منعطف/)).toBeInTheDocument();
  await userEvent.click(screen.getByRole("button", { name: "پیشرفت" }));
  expect(await screen.findByText("تحلیل کامل؛ در انتظار بررسی")).toBeInTheDocument();
});

it("labels legacy measurement provenance as uncertain", async () => {
  accessApi.getUserProgress.mockResolvedValue({ items: [{ id: "legacy-measurement", measured_at: "2026-10-01T08:00:00Z", weight_kg: 80, waist_circumference_cm: null, hip_circumference_cm: null, shoulder_circumference_cm: null, shoulder_width_cm: null, observed_fields: null }], total: 1, limit: 25, offset: 0 });
  renderDetail();
  await screen.findByRole("heading", { name: "خلاصه تعامل" });
  await userEvent.click(screen.getByRole("button", { name: "پیشرفت" }));
  expect(await screen.findByText(/رکورد تاریخی: مشخص نیست/)).toBeInTheDocument();
});
