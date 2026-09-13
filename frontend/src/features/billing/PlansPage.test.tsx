import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

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

beforeEach(() => {
  billingApi.getOffers.mockReset();
  entitlementState.snapshot = null;
  billingApi.getOffers.mockResolvedValue([
    offer(),
    offer({ offer_code: "training_6w", duration_weeks: 6, price_irr: 180000, is_available: false }),
    offer({ offer_code: "training_8w", duration_weeks: 8, price_irr: 240000 }),
  ]);
});

it("loads prices from the API and disables unavailable durations", async () => {
  const user = userEvent.setup();
  render(
    <MemoryRouter initialEntries={["/plans"]}>
      <Routes>
        <Route path="/plans" element={<PlansPage />} />
        <Route path="/billing/checkout/:offerCode" element={<span>checkout-placeholder</span>} />
      </Routes>
    </MemoryRouter>,
  );

  expect(await screen.findByRole("heading", { name: "پلن خودت را انتخاب کن" })).toBeInTheDocument();
  expect(screen.getByText(/۱۲۵٬۰۰۰/)).toBeInTheDocument();
  expect(screen.getByText(/۲۴۰٬۰۰۰/)).toBeInTheDocument();
  expect(screen.getByText("این پیشنهاد در دسترس نیست")).toBeInTheDocument();
  const unavailableButton = screen.getByRole("button", { name: /۶ هفته/ });
  expect(unavailableButton).toBeDisabled();

  await user.click(screen.getByRole("button", { name: /خرید.*۴ هفته/ }));
  await waitFor(() => expect(screen.getByText("checkout-placeholder")).toBeInTheDocument());
});

it("shows the current access and highlights offers matching a required entitlement", async () => {
  entitlementState.snapshot = {
    primary_package: "launch_trial",
    active_packages: ["launch_trial"],
    trial: { active: true, ends_at: "2026-09-30T12:00:00Z" },
    entitlements: { granted: ["body_analysis.run"], quotas: [] },
    grants: [],
  };
  billingApi.getOffers.mockResolvedValue([
    offer({ entitlements: ["body_analysis.run"] }),
    offer({ offer_code: "nutrition_4w", package_code: "nutrition", entitlements: ["nutrition.plan.generate"] }),
  ]);

  render(<MemoryRouter initialEntries={["/plans?required=body_analysis.run"]}><PlansPage /></MemoryRouter>);

  expect(await screen.findByText("دوره آزمایشی شروع")).toBeInTheDocument();
  expect(screen.getByText(/پایان دوره آزمایشی/)).toBeInTheDocument();
  expect(screen.getByTestId("billing-offer-training_4w")).toHaveClass("billing-offer--eligible");
  expect(screen.getByTestId("billing-offer-nutrition_4w")).not.toHaveClass("billing-offer--eligible");
});
