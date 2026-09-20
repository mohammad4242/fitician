import { fireEvent, render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";

jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));

import { useRouter } from "expo-router";

import { SignupCampaignCard } from "./SignupCampaignCard";

const mockPush = jest.fn();
const mockUseRouter = jest.mocked(useRouter);
const campaign = {
  code: "mobile-bonus",
  package_code: "complete" as const,
  duration_days: 42,
  term_weeks: 6 as const,
  available_until: null,
  public_badge_fa: "هدیه ثبت‌نام",
  public_badge_en: "Signup Gift",
  public_title_fa: "دوره کامل مهمان فیتیشن",
  public_title_en: "Your complete program is on us",
  public_message_fa: "ثبت‌نام کن و شروع کن.",
  public_message_en: "Create your account and start.",
  public_cta_fa: "هدیه‌ام رو بگیر",
  public_cta_en: "Claim my gift",
  show_on_landing: true,
  show_on_register: true,
};

beforeEach(() => {
  mockPush.mockClear();
  mockUseRouter.mockReturnValue({ push: mockPush } as never);
});

test("renders the public campaign in RTL and routes the Landing CTA to onboarding", () => {
  render(<SignupCampaignCard campaign={campaign} surface="landing" />);

  expect(screen.getByTestId("signup-campaign-card")).toBeTruthy();
  expect(screen.getByText("دوره کامل مهمان فیتیشن")).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "هدیه‌ام رو بگیر" }));
  expect(mockPush).toHaveBeenCalledWith("/public-onboarding");
});

test("renders no card for no campaign and no competing Register CTA", () => {
  const { rerender } = render(<SignupCampaignCard campaign={null} surface="landing" />);
  expect(screen.queryByTestId("signup-campaign-card")).toBeNull();

  rerender(<SignupCampaignCard campaign={campaign} surface="register" />);
  expect(screen.getByText("دوره کامل مهمان فیتیشن")).toBeTruthy();
  expect(screen.queryByRole("button", { name: "هدیه‌ام رو بگیر" })).toBeNull();
});
