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

it("renders Persian campaign copy and a fixed onboarding CTA on Landing", async () => {
  campaignApi.getActiveSignupCampaign.mockResolvedValue(campaign);
  renderBanner();

  expect(await screen.findByTestId("signup-campaign-banner")).toHaveTextContent("یک دوره کامل مهمان فیتیشن");
  expect(screen.getByText("هدیه ثبت‌نام")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: "هدیه‌ام رو بگیر" })).toHaveAttribute("href", "/get-started");
  expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalledWith("landing");
});

it("selects English campaign copy from resolvedLanguage", async () => {
  await i18n.changeLanguage("en");
  campaignApi.getActiveSignupCampaign.mockResolvedValue(campaign);
  renderBanner();

  expect(await screen.findByTestId("signup-campaign-banner")).toHaveTextContent("Your complete program is on us");
  expect(screen.getByRole("link", { name: "Claim my gift" })).toHaveAttribute("href", "/get-started");
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

  expect(await screen.findByTestId("signup-campaign-banner")).toHaveTextContent("یک دوره کامل مهمان فیتیشن");
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(campaignApi.getActiveSignupCampaign).toHaveBeenCalledWith("register");
});
