import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

const auth = vi.hoisted(() => ({
  register: vi.fn(),
}));
const campaignApi = vi.hoisted(() => ({
  getActiveSignupCampaign: vi.fn(),
}));

vi.mock("./AuthContext", () => ({
  useAuth: () => ({ register: auth.register }),
}));
vi.mock("../campaigns/publicCampaignApi", () => campaignApi);

import { RegisterPage } from "./RegisterPage";

beforeEach(() => {
  auth.register.mockReset();
  campaignApi.getActiveSignupCampaign.mockReset();
  campaignApi.getActiveSignupCampaign.mockResolvedValue(null);
});

const registerCampaign = {
  code: "register-bonus",
  package_code: "complete" as const,
  duration_days: 42,
  term_weeks: 6 as const,
  available_until: null,
  public_badge_fa: "هدیه ثبت‌نام",
  public_badge_en: "Signup Gift",
  public_title_fa: "حساب کامل مهمان فیتیشن",
  public_title_en: "Your complete account is on us",
  public_message_fa: "ثبت‌نام کن و شروع کن.",
  public_message_en: "Create your account and start.",
  public_cta_fa: "هدیه‌ام رو بگیر",
  public_cta_en: "Claim my gift",
  show_on_landing: true,
  show_on_register: true,
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <Routes>
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/dashboard" element={<div>dashboard reached</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

it("keeps registration controls usable without promotional media", () => {
  renderPage();

  expect(screen.queryByTestId("auth-training-accent")).not.toBeInTheDocument();
  expect(document.querySelector(".brand-panel")).not.toBeInTheDocument();
  expect(screen.getByLabelText("ایمیل")).toBeVisible();
  expect(screen.getByRole("button", { name: "ساخت حساب" })).toBeEnabled();
});

it("does not submit when password confirmation differs", async () => {
  const user = userEvent.setup();
  renderPage();

  await user.type(screen.getByLabelText("ایمیل"), "user@example.com");
  await user.type(screen.getByLabelText("رمز عبور"), "long password");
  await user.type(screen.getByLabelText("تکرار رمز عبور"), "different password");
  await user.click(screen.getByRole("button", { name: "ساخت حساب" }));

  expect(auth.register).not.toHaveBeenCalled();
  expect(screen.getByRole("alert")).toHaveTextContent("رمزها یکسان نیستند");
});

it("shows an active campaign above the registration form", async () => {
  campaignApi.getActiveSignupCampaign.mockResolvedValue(registerCampaign);
  renderPage();

  expect(await screen.findByTestId("signup-campaign-banner")).toHaveTextContent("حساب کامل مهمان فیتیشن");
  expect(screen.getByRole("button", { name: "ساخت حساب" })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "هدیه‌ام رو بگیر" })).not.toBeInTheDocument();
  expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalledWith("register");
});

it("keeps the normal form when the campaign request fails", async () => {
  campaignApi.getActiveSignupCampaign.mockRejectedValue(new Error("network"));
  renderPage();

  expect(await screen.findByLabelText("ایمیل")).toBeInTheDocument();
  expect(screen.queryByTestId("signup-campaign-banner")).not.toBeInTheDocument();
});

it("registers and navigates to the protected dashboard", async () => {
  auth.register.mockResolvedValue(undefined);
  const user = userEvent.setup();
  renderPage();

  await user.type(screen.getByLabelText("ایمیل"), "user@example.com");
  await user.type(screen.getByLabelText("رمز عبور"), "long password");
  await user.type(screen.getByLabelText("تکرار رمز عبور"), "long password");
  await user.click(screen.getByRole("button", { name: "ساخت حساب" }));

  expect(auth.register).toHaveBeenCalledWith({
    email: "user@example.com",
    password: "long password",
  });
  expect(auth.register).toHaveBeenCalledTimes(1);
  expect(await screen.findByText("dashboard reached")).toBeInTheDocument();
});
