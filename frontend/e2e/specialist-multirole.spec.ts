import { expect, test } from "@playwright/test";

import {
  apiJson,
  apiResponse,
  createE2EAccount,
  setupNutritionMember,
  setupWorkoutMember,
  type E2EAccount,
} from "./fixtures/specialist";

type WorkoutPlan = {
  id: string;
  status: string;
  days: Array<{ exercises: Array<{ sets: number; rir: number | null }> }>;
  coach_review: {
    state: string;
    coach_display_name: string | null;
    coach_note: string | null;
  };
};

type WorkoutReview = {
  id: string;
  source_plan_id: string;
  user_id: string;
  member_display_name: string | null;
  status: string;
  claimed_by_user_id: string | null;
  draft_revision: number;
};

type WorkoutReviewDetail = WorkoutReview & {
  draft: {
    days: Array<{ exercises: Array<{ sets: number; rir: number | null }> }>;
  } | null;
  coach_note: string | null;
};

type WorkoutHistoryItem = {
  id: string;
  status: string;
  is_active: boolean;
  coach_review: WorkoutPlan["coach_review"];
};

type NutritionPlan = {
  id: string;
  revision: number;
  lifecycle_status: string;
  physician_review_status: string | null;
  physician_approved: boolean;
  physician_display_name: string | null;
  physician_user_visible_notes: string | null;
  start_date: string;
};

type NutritionGeneration = {
  bundle_id: string | null;
  selected_plan_id: string | null;
  plan: NutritionPlan | null;
  budget_plan: NutritionPlan | null;
  ideal_plan: NutritionPlan | null;
};

type NutritionReview = {
  review_id: string;
  plan_id: string;
  user_id: string;
  member_display_name: string | null;
  status: string;
  physician_user_id: string | null;
};

type LabRequest = {
  requested_tests: string[];
  user_visible_reason: string | null;
};

async function closeAccounts(...accounts: E2EAccount[]) {
  await Promise.all(accounts.map((account) => account.context.close()));
}

async function expectSeparateSessions(...accounts: E2EAccount[]) {
  const sessionCookies = await Promise.all(
    accounts.map(async (account) => {
      const cookies = await account.context.cookies();
      return cookies.find((cookie) => cookie.name === "fitician_session")?.value;
    }),
  );
  expect(sessionCookies.every((value) => value !== undefined)).toBe(true);
  expect(new Set(sessionCookies).size).toBe(accounts.length);
}

async function selectNutritionPlanForReview(
  account: E2EAccount,
  generation: NutritionGeneration,
): Promise<NutritionPlan> {
  if (generation.selected_plan_id) {
    expect(generation.plan).not.toBeNull();
    if (!generation.plan) throw new Error("Selected nutrition plan was not returned");
    return generation.plan;
  }

  expect(generation.bundle_id).toBeTruthy();
  expect(generation.budget_plan).not.toBeNull();
  if (!generation.bundle_id || !generation.budget_plan) {
    throw new Error("Nutrition generation did not return a selectable plan bundle");
  }

  const selected = await apiJson<{
    selected_plan_id: string;
    selected_plan_role: string;
    plan: NutritionPlan;
  }>(account.context, `/api/v1/nutrition/plan-bundles/${generation.bundle_id}/select`, {
    method: "POST",
    data: { plan_id: generation.budget_plan.id },
  });
  expect(selected.selected_plan_id).toBe(generation.budget_plan.id);
  expect(selected.selected_plan_role).toBe("budget");
  return selected.plan;
}

test.describe("real specialist multi-role flows", () => {
  test("User -> Coach -> User proves the approved workout revision is isolated and active", async ({ browser }, testInfo) => {
    const runLabel = `${testInfo.project.name}-${testInfo.workerIndex}-${testInfo.retry}`;
    const member = await createE2EAccount(browser, "coach-member", { displayName: `کاربر تمرین ${runLabel}` });
    const coach = await createE2EAccount(browser, "coach-primary", {
      displayName: `مربی سارا ${runLabel}`,
      role: "coach",
    });
    const secondCoach = await createE2EAccount(browser, "coach-secondary", {
      displayName: `مربی دوم ${runLabel}`,
      role: "coach",
    });
    const admin = await createE2EAccount(browser, "admin-only", { admin: true });

    try {
      await expectSeparateSessions(member, coach, secondCoach, admin);
      await setupWorkoutMember(member.context, member.displayName);

      const generated = await apiJson<{ plan: WorkoutPlan }>(
        member.context,
        "/api/v1/workout-plans/generate",
        { method: "POST" },
      );
      expect(generated.plan.status).toBe("pending_review");
      expect(generated.plan.coach_review.state).toBe("pending_coach_review");

      const historyBefore = await apiJson<WorkoutHistoryItem[]>(
        member.context,
        "/api/v1/workout-plans/history",
      );
      const source = historyBefore.find((item) => item.id === generated.plan.id);
      expect(source?.status).toBe("pending_review");
      expect(source?.is_active).toBe(false);

      const memberCoachAccess = await apiResponse(member.context, "/api/v1/coach/workout-reviews");
      expect(memberCoachAccess.status()).toBe(403);
      const memberPhysicianAccess = await apiResponse(member.context, "/api/v1/nutrition/physician/access");
      expect(memberPhysicianAccess.status()).toBe(403);
      const adminPhysicianAccess = await apiResponse(admin.context, "/api/v1/nutrition/physician/access");
      expect(adminPhysicianAccess.status()).toBe(403);
      await member.page.goto("/coach/workouts", { waitUntil: "networkidle" });
      await expect(member.page).toHaveURL(/\/dashboard$/);
      await member.page.goto("/physician/nutrition", { waitUntil: "networkidle" });
      await expect(member.page).toHaveURL(/\/dashboard$/);

      const pendingReviews = await apiJson<WorkoutReview[]>(
        coach.context,
        "/api/v1/coach/workout-reviews?view=pending",
      );
      const review = pendingReviews.find((item) => item.source_plan_id === generated.plan.id);
      expect(review).toBeDefined();
      if (!review) throw new Error("Generated workout review was not in the coach queue");

      await coach.page.goto("/coach/workouts", { waitUntil: "networkidle" });
      const caseCard = coach.page.locator(".coach-review-cases article").filter({ hasText: member.displayName });
      await expect(caseCard).toHaveCount(1);
      await expect(caseCard).toBeVisible();
      await caseCard.getByRole("button", { name: /شروع بازبینی|Start review/ }).click();
      await expect(coach.page.locator(".coach-review-case-header")).toContainText(member.displayName);

      const claimed = await apiJson<WorkoutReviewDetail>(
        coach.context,
        `/api/v1/coach/workout-reviews/${review.id}`,
      );
      expect(claimed.status).toBe("claimed");
      expect(claimed.claimed_by_user_id).toBe(coach.userId);
      expect(claimed.draft?.days[0]?.exercises[0]?.sets).toBeGreaterThan(0);

      const secondClaim = await apiResponse(
        secondCoach.context,
        `/api/v1/coach/workout-reviews/${review.id}/claim`,
        { method: "POST" },
      );
      expect(secondClaim.status()).toBe(409);
      const secondDetail = await apiResponse(
        secondCoach.context,
        `/api/v1/coach/workout-reviews/${review.id}`,
      );
      expect(secondDetail.ok()).toBe(false);

      const rirInput = coach.page.getByLabel(/RIR روز/).first();
      const initialRir = Number(await rirInput.inputValue());
      const changedRir = initialRir === 0 ? 1 : initialRir - 1;
      await rirInput.fill(String(changedRir));
      await expect(rirInput).toHaveValue(String(changedRir));
      await coach.page.getByLabel("یادداشت مربی برای کاربر").fill("برای شروع ایمن‌تر تنظیم شد");
      const draftResponsePromise = coach.page.waitForResponse((response) => (
        response.url().includes(`/api/v1/coach/workout-reviews/${review.id}/draft`)
        && response.request().method() === "PUT"
      ));
      await coach.page.getByRole("button", { name: "ذخیره پیش‌نویس" }).click();
      const draftResponse = await draftResponsePromise;
      expect(draftResponse.ok()).toBe(true);

      await expect.poll(async () => (
        await apiJson<WorkoutReviewDetail>(coach.context, `/api/v1/coach/workout-reviews/${review.id}`)
      ).draft_revision).toBeGreaterThan(claimed.draft_revision);
      const savedDraft = await apiJson<WorkoutReviewDetail>(
        coach.context,
        `/api/v1/coach/workout-reviews/${review.id}`,
      );
      expect(savedDraft.draft?.days[0]?.exercises[0]?.rir).toBe(changedRir);
      expect(savedDraft.coach_note).toBe("برای شروع ایمن‌تر تنظیم شد");

      await coach.page.getByRole("button", { name: "تأیید و ارسال برای کاربر" }).click();
      await expect(coach.page.getByRole("tab", { name: /تأییدشده|Approved/ })).toHaveAttribute("aria-selected", "true");

      const approvedQueue = await apiJson<WorkoutReview[]>(
        coach.context,
        "/api/v1/coach/workout-reviews?view=approved",
      );
      expect(approvedQueue.find((item) => item.id === review.id)?.status).toBe("approved");

      const activePlan = await apiJson<WorkoutPlan>(member.context, "/api/v1/workout-plans/active");
      expect(activePlan.status).toBe("active");
      expect(activePlan.id).not.toBe(generated.plan.id);
      expect(activePlan.coach_review).toMatchObject({
        state: "coach_approved",
        coach_display_name: coach.displayName,
        coach_note: "برای شروع ایمن‌تر تنظیم شد",
      });
      expect(activePlan.days[0]?.exercises[0]?.rir).toBe(changedRir);

      const historyAfter = await apiJson<WorkoutHistoryItem[]>(
        member.context,
        "/api/v1/workout-plans/history",
      );
      expect(historyAfter.find((item) => item.id === generated.plan.id)).toMatchObject({
        status: "superseded",
        is_active: false,
      });
      expect(historyAfter.find((item) => item.id === activePlan.id)).toMatchObject({
        status: "active",
        is_active: true,
        coach_review: { state: "coach_approved" },
      });

      await member.page.goto("/workout-plan", { waitUntil: "networkidle" });
      await expect(member.page.locator(".workout-review-banner--approved")).toContainText(coach.displayName);
      await expect(member.page.locator(".workout-review-banner--approved")).toContainText("برای شروع ایمن‌تر تنظیم شد");
    } finally {
      await closeAccounts(member, coach, secondCoach, admin);
    }
  });

  test("User -> Physician -> User proves approval, medical isolation, and user-visible lab requests", async ({ browser }, testInfo) => {
    const runLabel = `${testInfo.project.name}-${testInfo.workerIndex}-${testInfo.retry}`;
    const patient = await createE2EAccount(browser, "physician-patient", { displayName: `پرونده فشار خون ${runLabel}` });
    const labPatient = await createE2EAccount(browser, "lab-patient", { displayName: `پرونده آزمایش ${runLabel}` });
    const physician = await createE2EAccount(browser, "physician-primary", {
      displayName: `دکتر نادری ${runLabel}`,
      role: "physician",
    });
    const secondPhysician = await createE2EAccount(browser, "physician-secondary", {
      displayName: `دکتر دوم ${runLabel}`,
      role: "physician",
    });

    try {
      await expectSeparateSessions(patient, labPatient, physician, secondPhysician);
      await setupNutritionMember(patient.context, patient.displayName, "فشار خون کنترل‌شده پرونده اول");
      await setupNutritionMember(labPatient.context, labPatient.displayName, "پرونده آزمایش مستقل");

      const patientGeneration = await apiJson<NutritionGeneration>(
        patient.context,
        "/api/v1/nutrition/plans",
        { method: "POST" },
      );
      const labPatientGeneration = await apiJson<NutritionGeneration>(
        labPatient.context,
        "/api/v1/nutrition/plans",
        { method: "POST" },
      );
      const patientPlan = await selectNutritionPlanForReview(patient, patientGeneration);
      const labPatientPlan = await selectNutritionPlanForReview(labPatient, labPatientGeneration);
      expect(patientPlan.lifecycle_status).toBe("pending_physician_review");
      expect(patientPlan.physician_review_status).toBe("pending");
      expect(labPatientPlan.lifecycle_status).toBe("pending_physician_review");

      const pendingReviews = await apiJson<NutritionReview[]>(
        physician.context,
        "/api/v1/nutrition/physician/reviews?view=pending",
      );
      const patientReview = pendingReviews.find((item) => item.plan_id === patientPlan.id);
      const labReview = pendingReviews.find((item) => item.plan_id === labPatientPlan.id);
      expect(patientReview?.member_display_name).toBe(patient.displayName);
      expect(labReview?.member_display_name).toBe(labPatient.displayName);
      if (!patientReview || !labReview) throw new Error("Generated nutrition reviews were not in the physician queue");

      await physician.page.goto("/physician/nutrition", { waitUntil: "networkidle" });
      const patientCard = physician.page.locator(".physician-review-cases article").filter({ hasText: patient.displayName });
      await expect(patientCard).toHaveCount(1);
      await expect(patientCard).toBeVisible();
      await patientCard.getByRole("button", { name: /شروع بررسی|Claim and view revision/ }).click();
      await expect(physician.page.locator(".physician-review-case-header")).toBeVisible();

      const claimedReviews = await apiJson<NutritionReview[]>(
        physician.context,
        "/api/v1/nutrition/physician/reviews?view=claimed",
      );
      expect(claimedReviews.find((item) => item.review_id === patientReview.review_id)).toMatchObject({
        status: "in_review",
        physician_user_id: physician.userId,
      });

      const medicalContext = await apiJson<{
        conditions: Array<{ code: string; details: string | null }>;
      }>(
        physician.context,
        `/api/v1/nutrition/physician/plans/${patientPlan.id}/medical-context`,
      );
      expect(medicalContext.conditions).toEqual([
        { code: "controlled_hypertension", details: "فشار خون کنترل‌شده پرونده اول" },
      ]);

      const secondContext = await apiResponse(
        secondPhysician.context,
        `/api/v1/nutrition/physician/plans/${patientPlan.id}/medical-context`,
      );
      expect(secondContext.ok()).toBe(false);
      const secondPlan = await apiResponse(
        secondPhysician.context,
        `/api/v1/nutrition/physician/plans/${patientPlan.id}`,
      );
      expect(secondPlan.ok()).toBe(false);
      const secondClaim = await apiResponse(
        secondPhysician.context,
        `/api/v1/nutrition/physician/reviews/${patientReview.review_id}/claim`,
        { method: "POST" },
      );
      expect(secondClaim.status()).toBe(409);
      const secondApprove = await apiResponse(
        secondPhysician.context,
        `/api/v1/nutrition/physician/plans/${patientPlan.id}/action`,
        {
          method: "POST",
          data: {
            expected_plan_revision_id: patientPlan.id,
            action: "approve",
            notes: null,
            internal_notes: null,
          },
        },
      );
      expect(secondApprove.status()).toBe(409);

      await physician.page.getByRole("tab", { name: "یادداشت‌ها" }).click();
      await physician.page.getByLabel("یادداشت قابل مشاهده برای کاربر").fill("نسخه با پایش منظم ادامه یابد");
      await physician.page.getByRole("tab", { name: "بررسی برنامه" }).click();
      await physician.page.getByRole("button", { name: "تأیید این نسخه" }).click();

      await expect.poll(async () => (
        await apiJson<NutritionReview[]>(physician.context, "/api/v1/nutrition/physician/reviews?view=approved")
      ).some((item) => item.review_id === patientReview.review_id && item.status === "approved")).toBe(true);

      const approvedPatient = await apiJson<NutritionPlan>(
        patient.context,
        `/api/v1/nutrition/plans/${patientPlan.id}`,
      );
      expect(approvedPatient).toMatchObject({
        lifecycle_status: "ready_to_start",
        physician_review_status: "approved",
        physician_approved: true,
        physician_display_name: physician.displayName,
        physician_user_visible_notes: "نسخه با پایش منظم ادامه یابد",
      });
      const activePatient = await apiJson<NutritionPlan>(
        patient.context,
        `/api/v1/nutrition/plans/${patientPlan.id}/start`,
        { method: "POST", data: { start_date: approvedPatient.start_date, timezone: "Asia/Tehran" } },
      );
      expect(activePatient.lifecycle_status).toBe("active");
      expect(activePatient.physician_review_status).toBe("approved");

      await patient.page.goto("/nutrition-estimate", { waitUntil: "networkidle" });
      await expect(patient.page.locator(".weekly-plan__notice")).toContainText("نسخه با پایش منظم ادامه یابد");

      const labCard = physician.page.locator(".physician-review-cases article").filter({ hasText: labPatient.displayName });
      await expect(labCard).toHaveCount(1);
      await expect(labCard).toBeVisible();
      await labCard.getByRole("button", { name: /شروع بررسی|Claim and view revision/ }).click();
      await physician.page.getByRole("tab", { name: "آزمایش‌ها" }).click();
      await physician.page.getByLabel("آزمایش‌های درخواستی").fill("CBC");
      await physician.page.getByRole("button", { name: "درخواست آزمایش" }).click();

      await expect.poll(async () => {
        const requests = await apiJson<LabRequest[]>(labPatient.context, "/api/v1/nutrition/lab-requests");
        return requests.find((item) => item.requested_tests.includes("CBC"));
      }).toBeTruthy();
      const labRequests = await apiJson<LabRequest[]>(labPatient.context, "/api/v1/nutrition/lab-requests");
      expect(labRequests).toEqual(expect.arrayContaining([
        expect.objectContaining({
          requested_tests: ["CBC"],
          user_visible_reason: "برای بررسی ایمن‌تر برنامه",
        }),
      ]));
    } finally {
      await closeAccounts(patient, labPatient, physician, secondPhysician);
    }
  });
});
