import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import "../../i18n";

const billingApi = vi.hoisted(() => ({
  getOffers: vi.fn(),
}));
const entitlementState = vi.hoisted(() => ({ snapshot: null as unknown }));

vi.mock("./api", () => billingApi);
vi.mock("../entitlements/EntitlementContext", () => ({
  useEntitlements: () => ({
    snapshot: entitlementState.snapshot,
    loading: false,
    error: null,
    refresh: vi.fn(async () => undefined),
    retry: vi.fn(),
    hasEntitlement: () => false,
    quotaFor: () => null,
  }),
}));

import { PlansPage } from "./PlansPage";

const offer = (overrides: Record<string, unknown> = {}) => ({
  offer_code: "training_4w",
  package_code: "training",
  duration_weeks: 4,
  price_irr: 125000,
  currency: "IRR",
  is_available: true,
  entitlements: ["training.plan.generate"],
  quota_policies: [],
  ...overrides,
});

const packageCodes = [
  "training",
  "training_coach",
  "nutrition",
  "nutrition_physician",
  "complete",
  "complete_care",
] as const;

const allOffers = packageCodes.flatMap((packageCode) => [4, 6, 8].map((duration) => offer({
  duration_weeks: duration,
  entitlements: packageCode === "nutrition" ? ["nutrition.plan.generate"] : ["body_analysis.run"],
  offer_code: `${packageCode}_${duration}w`,
  package_code: packageCode,
  price_irr: duration * 100_000,
  quota_policies: [{ entitlement: "body_analysis.run", limit: 1, window_days: 7 }],
})));

beforeEach(() => {
  billingApi.getOffers.mockReset();
  entitlementState.snapshot = null;
  billingApi.getOffers.mockResolvedValue([
    offer(),
    offer({ offer_code: "training_6w", duration_weeks: 6, price_irr: 180000, is_available: false }),
    offer({ offer_code: "training_8w", duration_weeks: 8, price_irr: 240000 }),
  ]);
});

function renderPlans(path = "/plans") {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/plans" element={<PlansPage />} />
        <Route path="/billing/checkout/:offerCode" element={<span>checkout-placeholder</span>} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("premium package pricing", () => {
it("groups six packages into three categories with one card and three durations each", async () => {
  const user = userEvent.setup();
  billingApi.getOffers.mockResolvedValue(allOffers);
  renderPlans();

  expect(await screen.findByRole("heading", { name: "بسته مناسب خودت را انتخاب کن" })).toBeInTheDocument();
  expect(screen.getAllByTestId(/^billing-package-/)).toHaveLength(2);
  expect(screen.getByTestId("billing-package-training")).toBeInTheDocument();
  expect(screen.getByTestId("billing-package-training_coach")).toBeInTheDocument();
  expect(screen.getAllByRole("radio", { name: /هفته/ })).toHaveLength(6);

  await user.click(screen.getByRole("tab", { name: "تغذیه" }));
  expect(screen.getByTestId("billing-package-nutrition")).toBeInTheDocument();
  expect(screen.getByTestId("billing-package-nutrition_physician")).toBeInTheDocument();

  await user.click(screen.getByRole("tab", { name: "کامل" }));
  expect(screen.getByTestId("billing-package-complete")).toBeInTheDocument();
  expect(screen.getByTestId("billing-package-complete_care")).toBeInTheDocument();
  expect(screen.getByText("کامل‌ترین بسته")).toBeInTheDocument();
});

it("changes price and quota when duration changes and checks out the selected offer", async () => {
  const user = userEvent.setup();
  billingApi.getOffers.mockResolvedValue(allOffers);
  renderPlans();

  const card = await screen.findByTestId("billing-package-training");
  expect(card).toHaveTextContent("۴۰۰٬۰۰۰ IRR");
  expect(card).toHaveTextContent("تا ۴ Body Analysis در طول دوره — هفته‌ای ۱ بار");
  await user.click(within(card).getByRole("radio", { name: "۶ هفته", checked: false }));
  expect(card).toHaveTextContent("۶۰۰٬۰۰۰ IRR");
  expect(card).toHaveTextContent("تا ۶ Body Analysis در طول دوره — هفته‌ای ۱ بار");

  await user.click(screen.getByRole("button", { name: /خرید.*تمرین هوشمند.*۶ هفته/ }));
  await waitFor(() => expect(screen.getByText("checkout-placeholder")).toBeInTheDocument());
});

it("disables checkout when the selected offer is unavailable", async () => {
  const user = userEvent.setup();
  billingApi.getOffers.mockResolvedValue([
    offer(),
    offer({ offer_code: "training_6w", duration_weeks: 6, price_irr: 180000, is_available: false }),
    offer({ offer_code: "training_8w", duration_weeks: 8, price_irr: 240000 }),
  ]);
  renderPlans();

  await screen.findByTestId("billing-package-training");
  await user.click(screen.getByRole("radio", { name: "۶ هفته" }));
  expect(screen.getByRole("button", { name: /خرید.*تمرین هوشمند.*۶ هفته/ })).toBeDisabled();
  expect(screen.getByText("این پیشنهاد در دسترس نیست")).toBeInTheDocument();
});

it("shows current and trial badges, defaults category, and highlights required entitlement", async () => {
  entitlementState.snapshot = {
    primary_package: "nutrition",
    active_packages: ["nutrition"],
    trial: { active: true, ends_at: "2026-09-30T12:00:00Z" },
    entitlements: { granted: ["body_analysis.run"], quotas: [] },
    grants: [{ id: "grant-1", package_code: "nutrition", source: "subscription", term_weeks: 4, starts_at: "2026-09-01T00:00:00Z", ends_at: "2026-10-01T00:00:00Z", revoked_at: null }],
  };
  billingApi.getOffers.mockResolvedValue([
    offer({ offer_code: "nutrition_4w", package_code: "nutrition", entitlements: ["body_analysis.run"] }),
    offer({ offer_code: "nutrition_6w", package_code: "nutrition", duration_weeks: 6, entitlements: ["body_analysis.run"] }),
    offer({ offer_code: "nutrition_8w", package_code: "nutrition", duration_weeks: 8, entitlements: ["body_analysis.run"] }),
    offer({ offer_code: "nutrition_physician_4w", package_code: "nutrition_physician", entitlements: ["nutrition.physician_review"] }),
  ]);

  renderPlans("/plans?required=body_analysis.run");

  expect(await screen.findByRole("tab", { name: "تغذیه", selected: true })).toBeInTheDocument();
  expect(screen.getByText("بسته فعلی")).toBeInTheDocument();
  expect(screen.getAllByText("فعال").length).toBeGreaterThan(0);
  expect(screen.getByText("دوره آزمایشی")).toBeInTheDocument();
  expect(screen.getByText(/پایان دوره آزمایشی/)).toBeInTheDocument();
  expect(screen.getByTestId("billing-package-nutrition")).toHaveClass("billing-package-card--eligible");
  expect(screen.getByTestId("billing-package-nutrition")).toHaveClass("billing-package-card--active");
  expect(screen.getByTestId("billing-package-nutrition_physician")).not.toHaveClass("billing-package-card--eligible");
});

it("shows four features by default and expands the remaining package features", async () => {
  const user = userEvent.setup();
  billingApi.getOffers.mockResolvedValue(allOffers);
  renderPlans();

  const card = await screen.findByTestId("billing-package-training");
  expect(card.querySelectorAll(".billing-feature-row")).toHaveLength(4);
  const toggle = within(card).getByRole("button", { name: "مشاهده همه امکانات" });
  expect(toggle).toHaveAttribute("aria-expanded", "false");
  await user.click(toggle);
  expect(card.querySelectorAll(".billing-feature-row")).toHaveLength(7);
  expect(within(card).getByRole("button", { name: "نمایش کمتر" })).toHaveAttribute("aria-expanded", "true");
  expect(card).toHaveTextContent("دسترسی کامل به کتابخانه حرکات فیتیشن");
});
});
