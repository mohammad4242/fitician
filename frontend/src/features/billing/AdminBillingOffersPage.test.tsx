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

const offerFamilies = [
  { package_code: "training", offer_code_prefix: "training" },
  { package_code: "training_coach", offer_code_prefix: "training_coach" },
  { package_code: "nutrition", offer_code_prefix: "nutrition" },
  { package_code: "nutrition_physician", offer_code_prefix: "nutrition_physician" },
  { package_code: "complete", offer_code_prefix: "complete" },
  { package_code: "complete_care", offer_code_prefix: "complete_care" },
] as const;

const adminOffers = offerFamilies.flatMap(({ package_code, offer_code_prefix }) =>
  ([4, 6, 8] as const).map((duration_weeks) => offer({
    package_code,
    offer_code: `${offer_code_prefix}_${duration_weeks}w`,
    duration_weeks,
  })),
);

beforeEach(() => {
  Object.values(adminApi).forEach((mock) => mock.mockReset());
  adminApi.getAdminBillingOffers.mockResolvedValue(adminOffers);
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

function categoryHeader(name: string) {
  return screen.getByRole("button", { name });
}

async function chooseDateTime(
  user: ReturnType<typeof userEvent.setup>,
  card: HTMLElement,
  label: string,
  date: { year: string; month: string; day: string },
) {
  await user.click(within(card).getByRole("button", { name: label }));
  await user.selectOptions(within(card).getByRole("combobox", { name: "تاریخ - سال" }), date.year);
  await user.selectOptions(within(card).getByRole("combobox", { name: "تاریخ - ماه" }), date.month);
  await user.selectOptions(within(card).getByRole("combobox", { name: "تاریخ - روز" }), date.day);
  const hour = within(card).getByRole("spinbutton", { name: "ساعت" });
  const minute = within(card).getByRole("spinbutton", { name: "دقیقه" });
  await user.clear(hour);
  await user.type(hour, "10");
  await user.clear(minute);
  await user.type(minute, "30");
  await user.click(within(card).getByRole("button", { name: "انتخاب" }));
}

it("starts with only the three top-level offer categories", async () => {
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  await screen.findByRole("button", { name: "تمرین" });

  expect(categoryHeader("تغذیه")).toHaveAttribute("aria-expanded", "false");
  expect(categoryHeader("کامل")).toHaveAttribute("aria-expanded", "false");
  expect(screen.queryByRole("heading", { name: "تمرین هوشمند" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /training_4w/ })).not.toBeInTheDocument();
});

it("opens training into smart and coach groups with four, six, and eight week offers", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));

  expect(categoryHeader("تمرین")).toHaveAttribute("aria-expanded", "true");
  expect(screen.getByRole("heading", { name: "تمرین هوشمند" })).toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "تمرین + مربی" })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /training_4w/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /training_6w/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /training_8w/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /training_coach_4w/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /training_coach_6w/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /training_coach_8w/ })).toBeInTheDocument();
});

it("keeps only one top-level category open", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  await user.click(categoryHeader("تغذیه"));

  expect(categoryHeader("تمرین")).toHaveAttribute("aria-expanded", "false");
  expect(categoryHeader("تغذیه")).toHaveAttribute("aria-expanded", "true");
  expect(screen.queryByRole("heading", { name: "تمرین هوشمند" })).not.toBeInTheDocument();
  expect(screen.getByRole("heading", { name: "تغذیه هوشمند" })).toBeInTheDocument();
});

it("keeps every offer collapsed until its header is activated", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const firstCard = screen.getByTestId("admin-offer-training_4w");
  const secondCard = screen.getByTestId("admin-offer-training_6w");

  expect(offerHeader("training_4w")).toHaveAttribute("aria-expanded", "false");
  expect(offerHeader("training_6w")).toHaveAttribute("aria-expanded", "false");
  expect(within(firstCard).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
  expect(within(secondCard).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
});

it("opens training_4w and exposes its form", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const card = screen.getByTestId("admin-offer-training_4w");
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

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const firstCard = screen.getByTestId("admin-offer-training_4w");
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

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const card = screen.getByTestId("admin-offer-training_4w");
  await user.click(offerHeader("training_4w"));
  await user.click(offerHeader("training_4w"));

  expect(offerHeader("training_4w")).toHaveAttribute("aria-expanded", "false");
  expect(within(card).queryByRole("spinbutton", { name: "قیمت" })).not.toBeInTheDocument();
});

it("shows code-defined package and duration while updating database price", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminBillingOffersPage /></MemoryRouter>);

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const card = screen.getByTestId("admin-offer-training_4w");
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

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const card = screen.getByTestId("admin-offer-training_4w");
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

  await screen.findByRole("button", { name: "تمرین" });
  await user.click(categoryHeader("تمرین"));
  const card = screen.getByTestId("admin-offer-training_4w");
  await user.click(offerHeader("training_4w"));
  await chooseDateTime(user, card, "شروع دسترسی", { year: "1405", month: "6", day: "29" });
  await chooseDateTime(user, card, "پایان دسترسی", { year: "1405", month: "7", day: "28" });
  await user.click(within(card).getByRole("button", { name: "ذخیره" }));

  expect(adminApi.updateAdminBillingOffer).toHaveBeenCalledWith("training_4w", {
    available_from: "2026-09-20T07:00:00.000Z",
    available_until: "2026-10-20T07:00:00.000Z",
  });
});
