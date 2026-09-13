import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const adminApi = vi.hoisted(() => ({
  getAdminBillingOffers: vi.fn(),
  updateAdminBillingOffer: vi.fn(),
}));
vi.mock("./adminApi", () => adminApi);

import { AdminBillingOffersPage } from "./AdminBillingOffersPage";

const offer = (overrides: Record<string, unknown> = {}) => ({
  offer_code: "training_4w",
  package_code: "training",
  duration_weeks: 4,
  price_irr: 125000,
  currency: "IRR",
  is_available: true,
  entitlements: ["training.plan.generate"],
  quota_policies: [],
  is_active: true,
  available_from: null,
  available_until: null,
  ...overrides,
});

beforeEach(() => {
  Object.values(adminApi).forEach((mock) => mock.mockReset());
  adminApi.getAdminBillingOffers.mockResolvedValue([
    offer(),
    offer({ offer_code: "training_6w", duration_weeks: 6, price_irr: 180000 }),
  ]);
  adminApi.updateAdminBillingOffer.mockImplementation(async (code: string, input: unknown) => {
    const update = input as Record<string, unknown>;
    return {
      ...offer({ offer_code: code }),
      ...update,
      price_irr: "price_irr" in update ? update.price_irr : 125000,
      is_available: true,
    };
  });
});

it("shows code-defined package and duration while updating database price", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  expect(within(card).getByText("۴ هفته")).toBeInTheDocument();
  const price = within(card).getByLabelText("قیمت");
  await user.clear(price);
  await user.type(price, "150000");
  await user.click(within(card).getByRole("button", { name: "ذخیره" }));

  expect(adminApi.updateAdminBillingOffer).toHaveBeenCalledWith("training_4w", {
    price_irr: 150000,
  });
  expect(within(card).getByText("قیمت به‌روز شد")).toBeInTheDocument();
});

it("disables an offer without exposing immutable package or duration controls", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  await user.click(within(card).getByRole("checkbox", { name: "فعال" }));
  await user.click(within(card).getByRole("button", { name: "ذخیره" }));

  expect(adminApi.updateAdminBillingOffer).toHaveBeenCalledWith("training_4w", {
    is_active: false,
  });
  expect(within(card).queryByRole("textbox", { name: /بسته|مدت/ })).not.toBeInTheDocument();
});
