import { fireEvent, render, screen, within } from "@testing-library/react";
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

function offerHeader(code: string) {
  return screen.getByRole("button", { name: new RegExp(code) });
}

it("keeps every offer collapsed until its header is activated", async () => {
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const firstCard = await screen.findByTestId("admin-offer-training_4w");
  const secondCard = screen.getByTestId("admin-offer-training_6w");

  expect(offerHeader("training_4w")).toHaveAttribute("aria-expanded", "false");
  expect(offerHeader("training_6w")).toHaveAttribute("aria-expanded", "false");
  expect(within(firstCard).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
  expect(within(secondCard).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
});

it("opens training_4w and exposes its form", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  const header = offerHeader("training_4w");
  await user.click(header);

  expect(header).toHaveAttribute("aria-expanded", "true");
  expect(header).toHaveAttribute("aria-controls", "admin-offer-panel-training_4w");
  expect(document.getElementById("admin-offer-panel-training_4w")).toHaveAttribute("aria-hidden", "false");
  expect(within(card).getByLabelText("قیمت")).toBeInTheDocument();
});

it("closes the previous offer when another offer opens", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const firstCard = await screen.findByTestId("admin-offer-training_4w");
  const secondCard = screen.getByTestId("admin-offer-training_6w");
  await user.click(offerHeader("training_4w"));
  await user.click(offerHeader("training_6w"));

  expect(offerHeader("training_4w")).toHaveAttribute("aria-expanded", "false");
  expect(offerHeader("training_6w")).toHaveAttribute("aria-expanded", "true");
  expect(within(firstCard).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
  expect(within(secondCard).getByLabelText("قیمت")).toBeInTheDocument();
});

it("closes an open offer when its header is clicked again", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  await user.click(offerHeader("training_4w"));
  await user.click(offerHeader("training_4w"));

  expect(offerHeader("training_4w")).toHaveAttribute("aria-expanded", "false");
  expect(within(card).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
});

it("shows code-defined package and duration while updating database price", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  await user.click(offerHeader("training_4w"));
  expect(within(card).getByText("۴ هفته")).toBeInTheDocument();
  const price = within(card).getByLabelText("قیمت");
  await user.clear(price);
  await user.type(price, "150000");
  await user.click(within(card).getByRole("button", { name: "ذخیره" }));

  expect(adminApi.updateAdminBillingOffer).toHaveBeenCalledWith("training_4w", {
    price_irr: 150000,
  });
  expect(within(card).getByText("پیشنهاد به‌روز شد")).toBeInTheDocument();
});

it("disables an offer without exposing immutable package or duration controls", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  await user.click(offerHeader("training_4w"));
  await user.click(within(card).getByRole("checkbox", { name: "فعال" }));
  await user.click(within(card).getByRole("button", { name: "ذخیره" }));

  expect(adminApi.updateAdminBillingOffer).toHaveBeenCalledWith("training_4w", {
    is_active: false,
  });
  expect(within(card).queryByRole("textbox", { name: /بسته|مدت/ })).not.toBeInTheDocument();
});

it("updates the offer availability window", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  const card = await screen.findByTestId("admin-offer-training_4w");
  await user.click(offerHeader("training_4w"));
  const availableFrom = within(card).getByLabelText("شروع دسترسی");
  const availableUntil = within(card).getByLabelText("پایان دسترسی");
  fireEvent.change(availableFrom, { target: { value: "2026-09-20T10:30" } });
  fireEvent.change(availableUntil, { target: { value: "2026-10-20T10:30" } });
  await user.click(within(card).getByRole("button", { name: "ذخیره" }));

  expect(adminApi.updateAdminBillingOffer).toHaveBeenCalledWith("training_4w", {
    available_from: new Date("2026-09-20T10:30").toISOString(),
    available_until: new Date("2026-10-20T10:30").toISOString(),
  });
});
