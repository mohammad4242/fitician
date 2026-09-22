import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import i18n from "../../i18n";

const campaignApi = vi.hoisted(() => ({ getActiveSignupCampaign: vi.fn() }));
vi.mock("./publicCampaignApi", () => campaignApi);

import { SignupCampaignBanner } from "./SignupCampaignBanner";

const campaign = {
  code: "autumn-welcome-1405",
  package_code: "complete" as const,
  duration_days: 42,
  term_weeks: 6 as const,
  available_until: "2026-10-06T08:00:00Z",
  public_badge_fa: "هدیه ثبت‌نام",
  public_badge_en: "Signup Gift",
  public_title_fa: "یک دوره کامل مهمان فیتیشن",
  public_title_en: "Your complete program is on us",
  public_message_fa: "ثبت‌نام کن و شروع کن.",
  public_message_en: "Create your account and start.",
  public_cta_fa: "هدیه‌ام رو بگیر",
  public_cta_en: "Claim my gift",
  show_on_landing: true,
  show_on_register: true,
};

beforeEach(async () => {
  campaignApi.getActiveSignupCampaign.mockReset();
  await i18n.changeLanguage("fa");
});

function renderBanner(surface: "landing" | "register" = "landing") {
  return render(
    <MemoryRouter>
      <SignupCampaignBanner surface={surface} />
    </MemoryRouter>,
  );
}

it("renders only the Persian complete-package offer as the Landing link", async () => {
  campaignApi.getActiveSignupCampaign.mockResolvedValue(campaign);
  renderBanner();

  const banner = await screen.findByTestId("signup-campaign-banner");
  expect(banner).toHaveTextContent("۶ هفته برنامه تمرین + تغذیه رایگان");
  expect(banner).not.toHaveTextContent("یک دوره کامل مهمان فیتیشن");
  expect(banner).not.toHaveTextContent("ثبت‌نام کن و شروع کن.");
  expect(banner).not.toHaveTextContent("هدیه ثبت‌نام");
  expect(banner).not.toHaveTextContent("روز دسترسی مهمان");
  expect(screen.getByRole("link", { name: "۶ هفته برنامه تمرین + تغذیه رایگان" })).toHaveAttribute("href", "/get-started");
  expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalledWith("landing");
});

it("renders only the English complete-package offer", async () => {
  await i18n.changeLanguage("en");
  campaignApi.getActiveSignupCampaign.mockResolvedValue(campaign);
  renderBanner();

  const banner = await screen.findByTestId("signup-campaign-banner");
  expect(banner).toHaveTextContent("6 weeks of training + nutrition free");
  expect(banner).not.toHaveTextContent("Your complete program is on us");
  expect(banner).not.toHaveTextContent("Create your account and start.");
  expect(banner).not.toHaveTextContent("Signup Gift");
  expect(screen.getByRole("link", { name: "6 weeks of training + nutrition free" })).toHaveAttribute("href", "/get-started");
});

it("renders no card for null responses or failed requests", async () => {
  campaignApi.getActiveSignupCampaign.mockResolvedValueOnce(null);
  const { rerender } = renderBanner();
  await waitFor(() => expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalled());
  expect(screen.queryByTestId("signup-campaign-banner")).not.toBeInTheDocument();

  campaignApi.getActiveSignupCampaign.mockRejectedValueOnce(new Error("service unavailable"));
  rerender(<SignupCampaignBanner surface="landing" />);
  await waitFor(() => expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalledTimes(2));
  expect(screen.queryByTestId("signup-campaign-banner")).not.toBeInTheDocument();
});

it("does not add a competing navigation CTA on registration", async () => {
  campaignApi.getActiveSignupCampaign.mockResolvedValue(campaign);
  renderBanner("register");

  expect(await screen.findByTestId("signup-campaign-banner")).toHaveTextContent("۶ هفته برنامه تمرین + تغذیه رایگان");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalledWith("register");
});

it.each([
  { package_code: "training" as const, term_weeks: 6 as const },
  { package_code: "complete" as const, term_weeks: null },
])("fails safely for an incompatible offer", async (override) => {
  campaignApi.getActiveSignupCampaign.mockResolvedValue({ ...campaign, ...override });
  renderBanner();

  await waitFor(() => expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalled());
  expect(screen.queryByTestId("signup-campaign-banner")).not.toBeInTheDocument();
});
