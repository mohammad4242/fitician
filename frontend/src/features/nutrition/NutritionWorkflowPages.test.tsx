import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import i18n from "../../i18n";
import * as api from "./api";
import { NutritionLabsPage } from "./NutritionLabsPage";
import { NutritionSupplementsPage } from "./NutritionSupplementsPage";
import { NutritionTrackingPage } from "./NutritionTrackingPage";
import { PhysicianNutritionReviewPage } from "./PhysicianNutritionReviewPage";
import type { DailyTrackingSummary, NutritionAdherence, WeeklyPlan } from "./types";

vi.mock("./api");
const entitlementAccess = vi.hoisted(() => ({ allowed: true }));
vi.mock("../entitlements/EntitlementContext", () => ({
  useEntitlements: () => ({
    snapshot: null,
    loading: false,
    error: null,
    retry: vi.fn(),
    hasEntitlement: () => entitlementAccess.allowed,
    quotaFor: () => null,
  }),
}));

afterEach(() => {
  vi.unstubAllEnvs();
});
import { localIsoDate } from "@fitician/core/local-date";

const today = localIsoDate();

const summary: DailyTrackingSummary = {
  entry_date: today,
  check_in_status: "mostly_on_plan",
  plan_revision_id: "plan-1",
  data_status: "sufficient",
  actual_totals: { energy_kcal: 1750, protein_g: 92 },
  entries: [{
    id: "entry-1",
    entry_date: today,
    plan_revision_id: null,
    planned_meal_id: null,
    food_id: "food-1",
    display_name: "Chicken breast",
    quantity_grams: 100,
    source: "catalogue_manual",
    confidence: "high",
    nutrients: { energy_kcal: 165, protein_g: 31 },
    warning_codes: [],
  }],
};

const adherence: NutritionAdherence = {
  start: today,
  end: today,
  days: [{
    date: today,
    status: "sufficient",
    calorie_adherence: 88,
    protein_adherence: 92,
    meal_adherence: 75,
    tracking_completeness: 90,
    exact_entry_ratio: 1,
    composite_score: 87,
    formula_version: "adherence-v1",
    planned: { energy_kcal: 2000, protein_g: 100 },
    actual: { energy_kcal: 1750, protein_g: 92 },
  }],
  weight_trend: [],
  weight_causality_claimed: false,
};

const physicianPlan = {
  id: "plan-1",
  revision: 1,
  weekly_cost_irr: 7_000_000,
  budget_status: "within_budget",
  input_snapshot: { safety_reason_codes: [] },
  price_snapshot: { status: "fresh" },
  food_data_manifest: { catalogue_version: "v1" },
  profile_summary: {
    display_name: "Member One",
    height_cm: 165,
    weight_kg: "68.20",
    fitness_goal: "lose_weight",
    training_location: "gym",
    training_days_per_week: 3,
    physical_limitations: null,
    training_cautions: [],
    nutrition: { food_items: [{ kind: "favourite", name: "ماست", details: null }] },
    medical: { flags: {}, conditions: [], medications: [{ name: "ویتامین دی", dosage: "روزانه", notes: null }] },
  },
  nutrients: {
    protein: { nutrient_code: "protein", planned: 100, unit: "g/day", status: "adequate" },
  },
  days: [{
    day_index: 0,
    plan_date: today,
    meals: [{
      id: "meal-1",
      name_fa: "ناهار",
      name_en: "Lunch",
      foods: [{ food_id: "food-1", name_fa: "سینه مرغ", name_en: "Chicken breast", grams: 100 }],
    }],
  }],
} as unknown as WeeklyPlan;

beforeEach(async () => {
  vi.clearAllMocks();
  entitlementAccess.allowed = true;
  await i18n.changeLanguage("en");
  vi.mocked(api.getDailyTracking).mockResolvedValue(summary);
  vi.mocked(api.getNutritionAdherence).mockResolvedValue(adherence);
  vi.mocked(api.listCatalogueFoods).mockResolvedValue([
    { id: "food-1", slug: "chicken", name_fa: "سینه مرغ", name_en: "Chicken breast", canonical_unit: "g" },
    { id: "food-2", slug: "lentils", name_fa: "عدس", name_en: "Lentils", canonical_unit: "g" },
  ]);
  vi.mocked(api.listRecentFoods).mockResolvedValue([]);
  vi.mocked(api.listFoodPhotoEstimates).mockResolvedValue([]);
  vi.mocked(api.getFoodPhotoEstimate).mockResolvedValue({} as api.FoodPhotoEstimate);
  vi.mocked(api.getTrackingHistory).mockResolvedValue([summary]);
  vi.mocked(api.listLabDocuments).mockResolvedValue([]);
  vi.mocked(api.listLabRequests).mockResolvedValue([]);
  vi.mocked(api.listSupplementOrders).mockResolvedValue([]);
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([]);
  vi.mocked(api.listSupplementCatalogue).mockResolvedValue([]);
  vi.mocked(api.listPhysicianSupplementOrders).mockResolvedValue([]);
});

it("shows planned versus actual tracking and saves photo corrections before confirmation", async () => {
  vi.stubEnv("TZ", "UTC");
  const user = userEvent.setup();
  vi.mocked(api.listRecentFoods).mockResolvedValue([{ food_id: "food-1", display_name: "Chicken breast", last_quantity_grams: 120, last_entry_date: today }]);
  vi.mocked(api.estimateFoodPhoto).mockResolvedValue({
    id: "estimate-1",
    overall_confidence: 0.8,
    needs_user_confirmation: true,
    macro_totals: { calories: 200, protein_g: 25, carbohydrate_g: 0, fat_g: 5 },
    macro_totals_complete: true,
    created_at: "2026-09-13T20:45:00Z",
    items: [{ item_id: "item-1", food_id: "food-1", name_guess: "Chicken", estimated_amount: 120, unit: "g", mapping_status: "verified" }],
  });
  vi.mocked(api.correctFoodPhotoItem).mockResolvedValue({
    id: "estimate-1",
    overall_confidence: 0.8,
    needs_user_confirmation: true,
    macro_totals: { calories: 250, protein_g: 30, carbohydrate_g: 0, fat_g: 6 },
    macro_totals_complete: true,
    items: [{ item_id: "item-1", food_id: "food-1", name_guess: "Chicken", estimated_amount: 150, unit: "g", mapping_status: "verified" }],
  });
  render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

  expect(await screen.findByText("Logged calories")).toBeInTheDocument();
  expect(screen.getByText("Planned calories")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Log manually/i }));
  expect(await screen.findByRole("button", { name: "Chicken breast · 120 g" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Food photo/i }));
  await user.click(screen.getByRole("checkbox", { name: /third-party image processing/i }));
  expect(screen.getByLabelText("Choose food photo")).toHaveAttribute(
    "accept",
    "image/jpeg,image/png,image/webp,image/heic,image/heif",
  );
  await user.upload(screen.getByLabelText("Choose food photo"), new File(["image"], "meal.jpg", { type: "image/jpeg" }));
  expect(await screen.findByRole("img", { name: "Meal photo preview" })).toBeInTheDocument();
  expect(screen.getByText("Sep 14, 2026")).toBeInTheDocument();
  expect(screen.getByText(/≈ 200/)).toBeInTheDocument();
  const amount = await screen.findByRole("spinbutton", { name: "Chicken amount" });
  await user.clear(amount);
  await user.type(amount, "150");
  await user.tab();

  await waitFor(() => expect(api.correctFoodPhotoItem).toHaveBeenCalledWith("estimate-1", "item-1", { estimated_amount: 150 }));
});

it("starts with both nutrition entry methods collapsed", async () => {
  render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

  const manual = await screen.findByRole("button", { name: /Log manually/i });
  const photo = screen.getByRole("button", { name: /Food photo/i });

  expect(manual).toHaveAttribute("aria-expanded", "false");
  expect(photo).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByText("Exact catalogue entry")).not.toBeInTheDocument();
  expect(screen.queryByText("Choose a meal photo")).not.toBeInTheDocument();
  expect(document.getElementById("nutrition-manual-entry-panel")).toBeNull();
  expect(document.getElementById("nutrition-photo-entry-panel")).toBeNull();
});

it("keeps only the selected nutrition entry workflow open and toggles it closed", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

  const manual = await screen.findByRole("button", { name: /Log manually/i });
  const photo = screen.getByRole("button", { name: /Food photo/i });

  await user.click(manual);
  expect(manual).toHaveAttribute("aria-expanded", "true");
  expect(photo).toHaveAttribute("aria-expanded", "false");
  expect(document.getElementById("nutrition-manual-entry-panel")).not.toBeNull();
  expect(document.getElementById("nutrition-photo-entry-panel")).toBeNull();

  await user.click(photo);
  expect(manual).toHaveAttribute("aria-expanded", "false");
  expect(photo).toHaveAttribute("aria-expanded", "true");
  expect(document.getElementById("nutrition-manual-entry-panel")).toBeNull();
  expect(document.getElementById("nutrition-photo-entry-panel")).not.toBeNull();

  await user.click(photo);
  expect(manual).toHaveAttribute("aria-expanded", "false");
  expect(photo).toHaveAttribute("aria-expanded", "false");
  expect(document.getElementById("nutrition-photo-entry-panel")).toBeNull();
});

it("keeps manual tracking available while locking food-photo analysis without access", async () => {
  const user = userEvent.setup();
  entitlementAccess.allowed = false;
  render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: /Log manually/i }));
  expect(screen.getByRole("group", { name: "Exact catalogue entry" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: /Food photo/i }));
  expect(screen.getByText("AI photo analysis is not included in your current access.")).toBeInTheDocument();
  expect(screen.getByLabelText("Choose food photo")).toBeDisabled();
});

it("places the entry hub before totals and the check-in after adherence", async () => {
  const { container } = render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);
  await screen.findByText("Logged calories");

  const hub = container.querySelector(".nutrition-entry-hub");
  const dailyPanel = container.querySelector(".nutrition-daily-panel");
  const adherenceCard = container.querySelector(".nutrition-adherence-card");
  const checkIn = container.querySelector(".nutrition-checkin");

  expect(hub).not.toBeNull();
  expect(dailyPanel).not.toBeNull();
  expect(adherenceCard).not.toBeNull();
  expect(checkIn).not.toBeNull();
  if (hub && dailyPanel && adherenceCard && checkIn) {
    expect(hub.compareDocumentPosition(dailyPanel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(adherenceCard.compareDocumentPosition(checkIn) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  }
});

it("keeps adherence rows collapsed while the date filter remains active", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

  const toggle = await screen.findByRole("button", { name: "Adherence trend" });
  const date = screen.getByLabelText("From");
  const contentId = toggle.getAttribute("aria-controls");
  const content = contentId ? document.getElementById(contentId) : null;
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  expect(content).toHaveAttribute("aria-hidden", "true");
  expect(date).toBeEnabled();

  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "true");
  expect(content).toHaveAttribute("aria-hidden", "false");

  await user.click(toggle);
  expect(toggle).toHaveAttribute("aria-expanded", "false");

  await waitFor(() => expect(api.getTrackingHistory).toHaveBeenCalled());
  vi.mocked(api.getNutritionAdherence).mockClear();
  vi.mocked(api.getTrackingHistory).mockClear();
  const selectedStart = `${today.slice(0, 8)}01`;
  fireEvent.change(date, { target: { value: selectedStart } });

  await waitFor(() => {
    expect(api.getNutritionAdherence).toHaveBeenCalledWith(selectedStart, today);
    expect(api.getTrackingHistory).toHaveBeenCalledWith(selectedStart, today);
  });
});

it("keeps exact catalogue and quick estimate submissions unchanged", async () => {
  const user = userEvent.setup();
  vi.mocked(api.addCatalogueFoodEntry).mockResolvedValue({});
  vi.mocked(api.addQuickApproximation).mockResolvedValue({});
  render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: /Log manually/i }));
  const catalogueGroup = screen.getByRole("group", { name: "Exact catalogue entry" });
  await user.selectOptions(within(catalogueGroup).getByRole("combobox", { name: "Food" }), "food-2");
  const grams = within(catalogueGroup).getByRole("spinbutton", { name: "Amount in grams" });
  await user.clear(grams);
  await user.type(grams, "175");
  await user.click(within(catalogueGroup).getByRole("button", { name: "Add catalogue food" }));

  await waitFor(() => expect(api.addCatalogueFoodEntry).toHaveBeenCalledWith({
    entry_date: today,
    food_id: "food-2",
    grams: 175,
    note: null,
  }));

  const estimateGroup = screen.getByRole("group", { name: "Quick estimate" });
  await user.type(within(estimateGroup).getByRole("textbox", { name: "Approximate calories" }), "430");
  await user.click(within(estimateGroup).getByRole("button", { name: "Add estimate" }));

  await waitFor(() => expect(api.addQuickApproximation).toHaveBeenCalledWith({
    entry_date: today,
    display_name: "Approximate meal",
    calories: 430,
    protein_g: null,
  }));
});

it("uploads laboratory metadata and can delete an owned document", async () => {
  const user = userEvent.setup();
  const document = { id: "lab-1", original_filename: "cbc.pdf", content_type: "application/pdf", byte_size: 10, test_date: today, laboratory_name: "Lab", user_note: "Annual panel", category: "CBC", review_status: "uploaded", review_notes: null, uploaded_at: `${today}T12:00:00Z` };
  vi.mocked(api.listLabDocuments)
    .mockResolvedValueOnce([document])
    .mockResolvedValueOnce([document])
    .mockResolvedValueOnce([]);
  vi.mocked(api.uploadLabDocument).mockResolvedValue({});
  vi.mocked(api.deleteLabDocument).mockResolvedValue();
  render(<MemoryRouter><NutritionLabsPage /></MemoryRouter>);

  expect(await screen.findByText("cbc.pdf")).toBeInTheDocument();
  await user.type(screen.getByLabelText("Laboratory name"), "Fitician Lab");
  await user.type(screen.getByLabelText("Category"), "Blood panel");
  await user.type(screen.getByLabelText("Note"), "Annual panel");
  await user.upload(screen.getByLabelText("Choose lab file"), new File(["pdf"], "result.pdf", { type: "application/pdf" }));
  expect(screen.getByText("result.pdf")).toBeInTheDocument();
  const labCard = screen.getByText("cbc.pdf").closest("article");
  expect(labCard).not.toBeNull();
  if (labCard) {
    expect(within(labCard).getByText("CBC")).toBeInTheDocument();
    expect(within(labCard).getByText("Annual panel")).toBeInTheDocument();
    expect(within(labCard).getByText("Uploaded")).toBeInTheDocument();
  }
  await waitFor(() => expect(api.uploadLabDocument).toHaveBeenCalledWith(expect.any(File), expect.objectContaining({ laboratoryName: "Fitician Lab", category: "Blood panel" })));
  await user.click(screen.getByRole("button", { name: "Delete" }));
  await waitFor(() => expect(api.deleteLabDocument).toHaveBeenCalledWith("lab-1"));
});

it("keeps existing lab records readable while locking new uploads without access", async () => {
  entitlementAccess.allowed = false;
  vi.mocked(api.listLabDocuments).mockResolvedValue([{
    id: "lab-1", original_filename: "cbc.pdf", content_type: "application/pdf", byte_size: 10,
    test_date: today, laboratory_name: "Lab", user_note: null, category: "CBC", review_status: "uploaded",
    review_notes: null, uploaded_at: `${today}T12:00:00Z`,
  }]);
  render(<MemoryRouter><NutritionLabsPage /></MemoryRouter>);

  expect(await screen.findByText("cbc.pdf")).toBeInTheDocument();
  expect(screen.getByLabelText("Choose lab file")).toBeDisabled();
  expect(screen.getByText(/Lab management access is required/)).toBeInTheDocument();
});

it("filters the member supplement history without exposing dose editing", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listSupplementOrders).mockResolvedValue([
    { id: "order-1", plan_id: "plan-1", supplement_id: "supplement-1", name: "Vitamin D", dose_amount: 1, dose_unit: "unit", daily_units: 1, frequency: "daily", duration_days: 30, instructions: "After food", rationale: null, status: "active", acknowledged_at: null, supplement_nutrient_contribution: {}, combined_exposure_safety: {} },
    { id: "order-2", plan_id: "plan-0", supplement_id: "supplement-2", name: "Iron", dose_amount: 1, dose_unit: "unit", daily_units: 1, frequency: "daily", duration_days: 14, instructions: "As directed", rationale: null, status: "completed", acknowledged_at: today, supplement_nutrient_contribution: {}, combined_exposure_safety: {} },
  ]);
  render(<MemoryRouter><NutritionSupplementsPage /></MemoryRouter>);

  expect(await screen.findByText("Vitamin D")).toBeInTheDocument();
  await user.selectOptions(screen.getByRole("combobox", { name: "Status" }), "completed");
  expect(screen.queryByText("Vitamin D")).not.toBeInTheDocument();
  expect(screen.getByText("Iron")).toBeInTheDocument();
  expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
});

it("keeps supplement history readable while locking member acknowledgement without access", async () => {
  entitlementAccess.allowed = false;
  vi.mocked(api.listSupplementOrders).mockResolvedValue([{
    id: "order-1", plan_id: "plan-1", supplement_id: "supplement-1", name: "Vitamin D", dose_amount: 1,
    dose_unit: "unit", daily_units: 1, frequency: "daily", duration_days: 30, instructions: "After food",
    rationale: null, status: "active", acknowledged_at: null, supplement_nutrient_contribution: {},
    combined_exposure_safety: {},
  }]);
  render(<MemoryRouter><NutritionSupplementsPage /></MemoryRouter>);

  expect(await screen.findByText("Vitamin D")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Acknowledge" })).toBeDisabled();
  expect(screen.getByText(/Supplement management access is required/)).toBeInTheDocument();
});

it("lets a physician claim an exact revision and choose replacements from the canonical catalogue", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([{ review_id: "review-1", plan_id: "plan-1", user_id: "user-1", member_display_name: "Member One", status: "pending", priority: 1, physician_user_id: null, requested_at: today, target_review_by: null, reviewed_at: null, overdue: false }]);
  vi.mocked(api.claimPhysicianReview).mockResolvedValue({});
  vi.mocked(api.getPhysicianPlan).mockResolvedValue(physicianPlan);
  vi.mocked(api.listPhysicianLabs).mockResolvedValue([]);
  vi.mocked(api.replacePhysicianFood).mockResolvedValue(physicianPlan);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "Claim and view revision" }));
  expect(await screen.findByText("Revision under review 1")).toBeInTheDocument();
  expect(screen.getByText("Nutrient validation")).toBeInTheDocument();
  await user.click(screen.getByText(/Day 1/));
  await user.click(screen.getByText("Lunch"));
  await user.selectOptions(screen.getByRole("combobox", { name: "Replace Chicken breast" }), "food-2");
  await waitFor(() => expect(api.replacePhysicianFood).toHaveBeenCalledWith("plan-1", "meal-1", "food-1", "food-2"));
});

it("keeps physician plan days and meals closed until opened", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([{ review_id: "review-1", plan_id: "plan-1", user_id: "user-1", member_display_name: "Member One", status: "pending", priority: 1, physician_user_id: null, requested_at: today, target_review_by: null, reviewed_at: null, overdue: false }]);
  vi.mocked(api.claimPhysicianReview).mockResolvedValue({});
  vi.mocked(api.getPhysicianPlan).mockResolvedValue(physicianPlan);
  vi.mocked(api.listPhysicianLabs).mockResolvedValue([]);
  vi.mocked(api.listPhysicianSupplementOrders).mockResolvedValue([]);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "Claim and view revision" }));

  const profileSummary = screen.getByText("Body and training");
  expect(profileSummary.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText("Gym")).not.toBeVisible();
  await user.click(profileSummary);
  expect(screen.getByText("Gym")).toBeVisible();

  const daySummary = screen.getByText(/Day 1/);
  expect(daySummary.closest("details")).not.toBeNull();
  expect(daySummary.closest("details")).not.toHaveAttribute("open");
  expect(screen.getByText("Chicken breast", { selector: ".physician-plan-foods span" })).not.toBeVisible();

  await user.click(daySummary);

  const mealSummary = screen.getByText("Lunch");
  expect(mealSummary.closest("details")).not.toHaveAttribute("open");
  await user.click(mealSummary);
  expect(screen.getByText("Chicken breast", { selector: ".physician-plan-foods span" })).toBeVisible();
});

it("switches from the physician queue into the selected case", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([{ review_id: "review-1", plan_id: "plan-1", user_id: "user-1", member_display_name: "Member One", status: "pending", priority: 1, physician_user_id: null, requested_at: today, target_review_by: null, reviewed_at: null, overdue: false }]);
  vi.mocked(api.claimPhysicianReview).mockResolvedValue({});
  vi.mocked(api.getPhysicianPlan).mockResolvedValue(physicianPlan);
  vi.mocked(api.listPhysicianLabs).mockResolvedValue([]);
  vi.mocked(api.listPhysicianSupplementOrders).mockResolvedValue([]);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  const workspace = document.querySelector(".physician-review-workspace");
  expect(workspace).not.toHaveClass("has-selected");
  await user.click(await screen.findByRole("button", { name: "Claim and view revision" }));

  expect(await screen.findByText("Revision under review 1")).toBeInTheDocument();
  expect(workspace).toHaveClass("has-selected");
  await user.click(screen.getByRole("button", { name: "Back to queue" }));
  expect(workspace).not.toHaveClass("has-selected");
});

it("separates physician queue views and keeps approved revisions read-only", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listPhysicianReviews).mockImplementation(async (view = "pending") => view === "approved"
    ? [{ review_id: "approved-1", plan_id: "plan-1", user_id: "user-1", member_display_name: "Member One", status: "approved", priority: 1, physician_user_id: "physician-1", requested_at: today, target_review_by: null, reviewed_at: today, overdue: false }]
    : []);
  vi.mocked(api.getPhysicianPlan).mockResolvedValue(physicianPlan);
  vi.mocked(api.listPhysicianLabs).mockResolvedValue([]);
  vi.mocked(api.listPhysicianSupplementOrders).mockResolvedValue([]);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  expect(await screen.findByRole("tab", { name: /Approved \(1\)/ })).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: /Approved/ }));
  await user.click(screen.getByRole("button", { name: "View revision" }));
  expect(await screen.findByText("Revision under review 1")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Approve this revision" })).not.toBeInTheDocument();
  await user.click(screen.getByText(/Day 1/));
  await user.click(screen.getByText("Lunch"));
  expect(screen.getByRole("spinbutton", { name: "Chicken breast quantity" })).toBeDisabled();
});

it("groups physician cases by requested date in every queue view", async () => {
  const user = userEvent.setup();
  const newerRequestedAt = new Date().toISOString();
  const olderRequestedAt = new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString();
  const queues: Record<api.PhysicianQueueView, api.PhysicianReviewQueueItem[]> = {
    pending: [
      { review_id: "old-pending", plan_id: "old-plan", user_id: "old-user", member_display_name: "Old Member", status: "pending", priority: 1, physician_user_id: null, requested_at: olderRequestedAt, target_review_by: null, reviewed_at: null, overdue: false },
      { review_id: "new-pending", plan_id: "new-plan", user_id: "new-user", member_display_name: "New Member", status: "pending", priority: 1, physician_user_id: null, requested_at: newerRequestedAt, target_review_by: null, reviewed_at: null, overdue: false },
    ],
    claimed: [
      { review_id: "old-claimed", plan_id: "old-plan", user_id: "old-user", member_display_name: "Old Member", status: "in_review", priority: 1, physician_user_id: "physician-1", requested_at: olderRequestedAt, target_review_by: null, reviewed_at: null, overdue: false },
      { review_id: "new-claimed", plan_id: "new-plan", user_id: "new-user", member_display_name: "New Member", status: "in_review", priority: 1, physician_user_id: "physician-1", requested_at: newerRequestedAt, target_review_by: null, reviewed_at: null, overdue: false },
    ],
    approved: [
      { review_id: "old-approved", plan_id: "old-plan", user_id: "old-user", member_display_name: "Old Member", status: "approved", priority: 1, physician_user_id: "physician-1", requested_at: olderRequestedAt, target_review_by: null, reviewed_at: newerRequestedAt, overdue: false },
      { review_id: "new-approved", plan_id: "new-plan", user_id: "new-user", member_display_name: "New Member", status: "approved", priority: 1, physician_user_id: "physician-1", requested_at: newerRequestedAt, target_review_by: null, reviewed_at: newerRequestedAt, overdue: false },
    ],
  };
  vi.mocked(api.listPhysicianReviews).mockImplementation(async (view = "pending") => queues[view]);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: /Today/ })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "6 weeks ago" })).toBeInTheDocument();
  expect(screen.getAllByRole("article").map((article) => article.textContent)).toEqual([
    expect.stringContaining("New Member"),
    expect.stringContaining("Old Member"),
  ]);

  await user.click(screen.getByRole("tab", { name: /Claimed/ }));
  expect(screen.getByRole("heading", { name: /Today/ })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "6 weeks ago" })).toBeInTheDocument();
  expect(screen.getAllByRole("article").map((article) => article.textContent)).toEqual([
    expect.stringContaining("New Member"),
    expect.stringContaining("Old Member"),
  ]);

  await user.click(screen.getByRole("tab", { name: /Approved/ }));
  expect(screen.getByRole("heading", { name: /Today/ })).toBeInTheDocument();
  expect(screen.queryByRole("heading", { name: "6 weeks ago" })).not.toBeInTheDocument();
  expect(screen.getAllByRole("article").map((article) => article.textContent)).toEqual([
    expect.stringContaining("Old Member"),
    expect.stringContaining("New Member"),
  ]);
});

it("localizes physician recency group headings in Persian", async () => {
  await i18n.changeLanguage("fa");
  const now = new Date().toISOString();
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([
    { review_id: "today", plan_id: "today-plan", user_id: "today-user", member_display_name: "کاربر امروز", status: "pending", priority: 1, physician_user_id: null, requested_at: now, target_review_by: null, reviewed_at: null, overdue: false },
    { review_id: "month", plan_id: "month-plan", user_id: "month-user", member_display_name: "کاربر قدیمی", status: "pending", priority: 1, physician_user_id: null, requested_at: new Date(Date.now() - 45 * 24 * 60 * 60 * 1000).toISOString(), target_review_by: null, reviewed_at: null, overdue: false },
  ]);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: /امروز/ })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "۶ هفته قبل" })).toBeInTheDocument();
});

it("lays out physician cases in a desk sidebar with clinical workspace tabs", async () => {
  const user = userEvent.setup();
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([
    { review_id: "review-1", plan_id: "plan-1", user_id: "user-1", member_display_name: "Member One", status: "pending", priority: 1, physician_user_id: null, requested_at: today, target_review_by: null, reviewed_at: null, overdue: false },
  ]);
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  expect(await screen.findByText("Physician desk")).toBeInTheDocument();
  expect(screen.getByText("Member One").closest("aside")).toHaveClass("physician-review-queue");
  vi.mocked(api.claimPhysicianReview).mockResolvedValue({});
  vi.mocked(api.getPhysicianPlan).mockResolvedValue(physicianPlan);
  vi.mocked(api.listPhysicianLabs).mockResolvedValue([]);
  await user.click(screen.getByRole("button", { name: "Claim and view revision" }));
  expect(screen.getByRole("tab", { name: "Plan review" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Laboratory review" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Supplements" })).toBeInTheDocument();
  expect(screen.getByRole("tab", { name: "Notes" })).toBeInTheDocument();
});

it("resets case-scoped physician notes before requesting labs for another member", async () => {
  const user = userEvent.setup();
  const secondPlan = { ...physicianPlan, id: "plan-2", revision: 2 } as unknown as WeeklyPlan;
  vi.mocked(api.listPhysicianReviews).mockResolvedValue([
    { review_id: "review-1", plan_id: "plan-1", user_id: "user-1", member_display_name: "Member One", status: "pending", priority: 1, physician_user_id: null, requested_at: today, target_review_by: null, reviewed_at: null, overdue: false },
    { review_id: "review-2", plan_id: "plan-2", user_id: "user-2", member_display_name: "Member Two", status: "pending", priority: 1, physician_user_id: null, requested_at: today, target_review_by: null, reviewed_at: null, overdue: false },
  ]);
  vi.mocked(api.claimPhysicianReview).mockResolvedValue({});
  vi.mocked(api.getPhysicianPlan).mockImplementation(async (planId) => planId === "plan-2" ? secondPlan : physicianPlan);
  vi.mocked(api.listPhysicianLabs).mockResolvedValue([]);
  vi.mocked(api.listPhysicianSupplementOrders).mockResolvedValue([]);
  vi.mocked(api.requestPhysicianLabs).mockResolvedValue({});
  render(<MemoryRouter><PhysicianNutritionReviewPage /></MemoryRouter>);

  const firstCase = (await screen.findByText("Member One")).closest("article");
  expect(firstCase).not.toBeNull();
  if (!firstCase) throw new Error("Member One queue case was not rendered");
  await user.click(within(firstCase).getByRole("button", { name: "Claim and view revision" }));
  await user.click(await screen.findByRole("tab", { name: "Notes" }));
  await user.type(screen.getByLabelText("User-visible note"), "First member note");

  const secondCase = (await screen.findByText("Member Two")).closest("article");
  expect(secondCase).not.toBeNull();
  if (!secondCase) throw new Error("Member Two queue case was not rendered");
  await user.click(within(secondCase).getByRole("button", { name: "Claim and view revision" }));
  expect(await screen.findByText("Revision under review 2")).toBeInTheDocument();
  await user.click(screen.getByRole("tab", { name: "Notes" }));
  expect(screen.getByLabelText("User-visible note")).toHaveValue("");
  await user.click(screen.getByRole("tab", { name: "Laboratory review" }));
  await user.click(screen.getByRole("button", { name: "Request labs" }));

  await waitFor(() => expect(api.requestPhysicianLabs).toHaveBeenCalledWith(
    "plan-2",
    ["CBC"],
    "For a safer plan review",
  ));
});

describe("Food photo nutrition estimation redesigned flow", () => {
  const completeEstimate: api.FoodPhotoEstimate = {
    id: "estimate-1",
    overall_confidence: 0.85,
    needs_user_confirmation: true,
    macro_totals: { calories: 350, protein_g: 40, carbohydrate_g: 20, fat_g: 10 },
    macro_totals_complete: true,
    items: [
      {
        item_id: "item-1",
        food_id: "food-1",
        name_guess: "Chicken breast",
        estimated_amount: 150,
        unit: "g",
        mapping_status: "resolved",
      },
    ],
  };

  const incompleteEstimate: api.FoodPhotoEstimate = {
    id: "estimate-2",
    overall_confidence: 0.7,
    needs_user_confirmation: true,
    macro_totals: { calories: 200, protein_g: 25, carbohydrate_g: 0, fat_g: 5 },
    macro_totals_complete: false,
    items: [
      {
        item_id: "item-1",
        food_id: "food-1",
        name_guess: "Chicken breast",
        estimated_amount: 100,
        unit: "g",
        mapping_status: "resolved",
      },
      {
        item_id: "item-2",
        food_id: null,
        name_guess: "Unknown sauce",
        estimated_amount: 50,
        unit: "unknown",
        mapping_status: "unresolved",
      },
    ],
  };

  async function openAndUpload(user: ReturnType<typeof userEvent.setup>) {
    expect(await screen.findByText("Logged calories")).toBeInTheDocument();
    await user.click(await screen.findByRole("button", { name: /Food photo/i }));
    await user.click(screen.getByRole("checkbox", { name: /third-party image processing/i }));
    const fileInput = screen.getByLabelText("Choose food photo");
    await waitFor(() => expect(fileInput).toBeEnabled());
    await user.upload(
      fileInput,
      new File(["image"], "meal.jpg", { type: "image/jpeg" })
    );
    expect(await screen.findByRole("img", { name: "Meal photo preview" })).toBeInTheDocument();
  }

  it("A: renders calories prominently and macros immediately after upload", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(completeEstimate);
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);

    expect(await screen.findByText("Estimated calories")).toBeInTheDocument();
    expect(screen.getByText("≈ 350 kcal")).toBeInTheDocument();
    expect(screen.getByText("≈ 40 g")).toBeInTheDocument();
    expect(screen.getByText("≈ 20 g")).toBeInTheDocument();
    expect(screen.getByText("≈ 10 g")).toBeInTheDocument();
    expect(screen.queryByText(/Partial estimate/i)).not.toBeInTheDocument();
  });

  it("keeps queued analysis interactive and refreshes the result in the background", async () => {
    const user = userEvent.setup();
    const queuedEstimate: api.FoodPhotoEstimate = {
      id: "estimate-queued",
      status: "queued",
      items: [],
      overall_confidence: null,
      needs_user_confirmation: true,
      macro_totals: { calories: 0, protein_g: 0, carbohydrate_g: 0, fat_g: 0 },
      macro_totals_complete: false,
    };
    const completedEstimate = { ...completeEstimate, id: "estimate-queued", status: "estimated" as const };
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(queuedEstimate);
    vi.mocked(api.getFoodPhotoEstimate).mockResolvedValue(completedEstimate);
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    await waitFor(() => expect(document.querySelector(".nutrition-photo-status")).toHaveTextContent("Photo analysis is queued"));
    expect(screen.queryByText("Estimated calories")).not.toBeInTheDocument();

    await waitFor(() => expect(api.getFoodPhotoEstimate).toHaveBeenCalledWith("estimate-queued"), { timeout: 4_000 });
    expect(await screen.findByText("Estimated calories")).toBeInTheDocument();
    expect(screen.getByText("≈ 350 kcal")).toBeInTheDocument();
    expect(api.getFoodPhotoEstimate).toHaveBeenCalledWith("estimate-queued");
  });

  it("B: keeps detection details collapsed by default", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(completeEstimate);
    const { container } = render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    await screen.findByText("Estimated calories");

    const details = container.querySelector("details.nutrition-photo-details");
    expect(details).not.toBeNull();
    expect(details).not.toHaveAttribute("open");
  });

  it("C: allows updating item amount in detection details", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(completeEstimate);
    vi.mocked(api.correctFoodPhotoItem).mockResolvedValue({
      ...completeEstimate,
      macro_totals: { calories: 420, protein_g: 48, carbohydrate_g: 20, fat_g: 12 },
      items: [{ ...completeEstimate.items[0], estimated_amount: 180 }],
    });
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    const amountInput = await screen.findByRole("spinbutton", { name: "Chicken breast amount" });
    await user.clear(amountInput);
    await user.type(amountInput, "180");
    await user.tab();

    await waitFor(() =>
      expect(api.correctFoodPhotoItem).toHaveBeenCalledWith("estimate-1", "item-1", {
        estimated_amount: 180,
      })
    );
  });

  it("D: allows removing an item from the estimate", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(completeEstimate);
    vi.mocked(api.correctFoodPhotoItem).mockResolvedValue({
      ...completeEstimate,
      items: [],
      macro_totals: { calories: 0, protein_g: 0, carbohydrate_g: 0, fat_g: 0 },
    });
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    const removeBtn = await screen.findByRole("button", { name: "Remove" });
    await user.click(removeBtn);

    await waitFor(() =>
      expect(api.correctFoodPhotoItem).toHaveBeenCalledWith("estimate-1", "item-1", {
        remove: true,
      })
    );
  });

  it("E: displays Needs review and food catalogue selector for unresolved items", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(incompleteEstimate);
    vi.mocked(api.correctFoodPhotoItem).mockResolvedValue({
      ...completeEstimate,
      id: "estimate-2",
    });
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    expect(await screen.findByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Matched")).toBeInTheDocument();

    const select = screen.getByRole("combobox", { name: "Choose food for Unknown sauce" });
    await user.selectOptions(select, "food-2");
    const gramInput = screen.getByRole("spinbutton", { name: "Unknown sauce amount in grams" });
    await user.type(gramInput, "60");

    const applyBtn = screen.getByRole("button", { name: "Apply" });
    expect(applyBtn).toBeEnabled();
    await user.click(applyBtn);

    await waitFor(() =>
      expect(api.correctFoodPhotoItem).toHaveBeenCalledWith("estimate-2", "item-2", {
        food_id: "food-2",
        estimated_amount: 60,
      })
    );
  });

  it("F: disables confirm button and displays guidance when estimate is incomplete", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(incompleteEstimate);
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    expect(await screen.findByText("Partial estimate — review the items below to complete the result.")).toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: "Confirm and log" });
    expect(confirmBtn).toBeDisabled();
  });

  it("G: enables confirm button and logs food once estimate is complete", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(completeEstimate);
    vi.mocked(api.confirmFoodPhoto).mockResolvedValue({});
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    const confirmBtn = await screen.findByRole("button", { name: "Confirm and log" });
    expect(confirmBtn).toBeEnabled();

    await user.click(confirmBtn);
    await waitFor(() =>
      expect(api.confirmFoodPhoto).toHaveBeenCalledWith("estimate-1", today)
    );
  });

  it("H: confirms Free Meal preview and preserves return navigation", async () => {
    const user = userEvent.setup();
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(completeEstimate);
    vi.mocked(api.confirmFreeMealPhotoPreview).mockResolvedValue({
      calories: 350,
      protein_g: 40,
      carbohydrate_g: 20,
      fat_g: 10,
    });
    render(
      <MemoryRouter initialEntries={["/tracking?freeMealId=meal-42&return=/nutrition-estimate"]}>
        <NutritionTrackingPage />
      </MemoryRouter>
    );

    expect(await screen.findByText("Logged calories")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Food photo/i })).toHaveAttribute("aria-expanded", "true");
    await user.click(screen.getByRole("checkbox", { name: /third-party image processing/i }));
    const fileInput = screen.getByLabelText("Choose food photo");
    await waitFor(() => expect(fileInput).toBeEnabled());
    await user.upload(
      fileInput,
      new File(["image"], "meal.jpg", { type: "image/jpeg" })
    );
    expect(await screen.findByRole("img", { name: "Meal photo preview" })).toBeInTheDocument();

    const confirmBtn = await screen.findByRole("button", {
      name: "Confirm and return to Free Meal",
    });
    expect(confirmBtn).toBeEnabled();
    await user.click(confirmBtn);

    await waitFor(() =>
      expect(api.confirmFreeMealPhotoPreview).toHaveBeenCalledWith("estimate-1")
    );
  });

  it("I: unmapped food with direct AI macros is considered ready without review and enables confirm immediately", async () => {
    const user = userEvent.setup();
    const directAiEstimate: api.FoodPhotoEstimate = {
      id: "estimate-direct",
      overall_confidence: 0.9,
      needs_user_confirmation: true,
      macro_totals: { calories: 610, protein_g: 57, carbohydrate_g: 60, fat_g: 15 },
      macro_totals_complete: true,
      items: [
        {
          item_id: "item-joojeh",
          food_id: null,
          name_guess: "Joojeh Kabab",
          estimated_amount: 250,
          unit: "g",
          mapping_status: "unresolved",
          calories: 350,
          protein_g: 52,
          carbohydrate_g: 2,
          fat_g: 14,
        },
      ],
    };
    vi.mocked(api.estimateFoodPhoto).mockResolvedValue(directAiEstimate);
    vi.mocked(api.confirmFoodPhoto).mockResolvedValue({});
    render(<MemoryRouter><NutritionTrackingPage /></MemoryRouter>);

    await openAndUpload(user);
    expect(await screen.findByText("Estimated calories")).toBeInTheDocument();
    expect(screen.getByText("≈ 610 kcal")).toBeInTheDocument();
    expect(screen.queryByText(/Partial estimate/i)).not.toBeInTheDocument();
    expect(screen.getByText("AI estimated")).toBeInTheDocument();
    expect(screen.queryByText("Needs review")).not.toBeInTheDocument();

    const confirmBtn = screen.getByRole("button", { name: "Confirm and log" });
    expect(confirmBtn).toBeEnabled();
    await user.click(confirmBtn);
    await waitFor(() =>
      expect(api.confirmFoodPhoto).toHaveBeenCalledWith("estimate-direct", today)
    );
  });
});
