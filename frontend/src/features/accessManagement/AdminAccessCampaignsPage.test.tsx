import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const accessApi = vi.hoisted(() => ({
  activateCampaign: vi.fn(),
  adminAccessPackageCodes: ["training", "training_coach", "complete", "complete_care"],
  createCampaign: vi.fn(),
  deactivateCampaign: vi.fn(),
  getCampaigns: vi.fn(),
  updateCampaign: vi.fn(),
}));
vi.mock("./adminAccessApi", () => accessApi);

import { AdminAccessCampaignsPage } from "./AdminAccessCampaignsPage";

const launchTrial = {
  id: "launch-1",
  code: "launch_trial_v1",
  name: "Fitition Launch Trial",
  description: null,
  kind: "signup_trial" as const,
  package_code: "launch_trial" as const,
  duration_days: 30,
  term_weeks: 4 as const,
  available_from: null,
  available_until: null,
  is_active: true,
  max_total_redemptions: null,
  redemption_count: 4,
  created_by_user_id: null,
  created_at: "2026-09-13T08:00:00Z",
  updated_at: "2026-09-13T08:00:00Z",
};

const manual = {
  ...launchTrial,
  id: "manual-1",
  code: "beta-promotion",
  name: "Beta promotion",
  kind: "manual_promotion" as const,
  package_code: "complete_care" as const,
  duration_days: 60,
  term_weeks: 8 as const,
  is_active: false,
  redemption_count: 0,
};

beforeEach(() => {
  accessApi.activateCampaign.mockReset();
  accessApi.createCampaign.mockReset();
  accessApi.deactivateCampaign.mockReset();
  accessApi.getCampaigns.mockReset();
  accessApi.updateCampaign.mockReset();
  accessApi.getCampaigns.mockResolvedValue([launchTrial, manual]);
  accessApi.deactivateCampaign.mockResolvedValue({ ...launchTrial, is_active: false });
  accessApi.activateCampaign.mockResolvedValue({ ...manual, is_active: true });
  accessApi.createCampaign.mockResolvedValue(manual);
  accessApi.updateCampaign.mockResolvedValue({ ...manual, name: "Updated promotion" });
});

it("lists campaign semantics and activates or deactivates without entitlement toggles", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  expect(await screen.findByRole("heading", { name: "کمپین‌ها و Trialها" })).toBeInTheDocument();
  expect(screen.getByText("این کمپین فقط هنگام ساخت حساب جدید به کاربر واجد شرایط داده می‌شود.")).toBeInTheDocument();
  expect(screen.getByText("این کمپین فقط توسط ادمین برای کاربر انتخاب‌شده اعمال می‌شود.")).toBeInTheDocument();
  expect(screen.getByText("پس از اولین ردیم، بسته، مدت و مدت تمرین قابل تغییر نیست.")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox", { name: /body_analysis|training\.plan/ })).not.toBeInTheDocument();

  const launchCard = screen.getByTestId("access-campaign-launch_trial_v1");
  await user.click(within(launchCard).getByRole("button", { name: "غیرفعال‌سازی" }));

  expect(accessApi.deactivateCampaign).toHaveBeenCalledWith("launch-1");
});

it("creates a package campaign from the admin form", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  await user.type(screen.getByLabelText("کد"), "spring-2027");
  await user.type(screen.getByLabelText("نام کمپین"), "Spring 2027");
  await user.selectOptions(screen.getByLabelText("بسته"), "training_coach");
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), "4");
  await user.clear(screen.getByLabelText("مدت مزیت (روز)"));
  await user.type(screen.getByLabelText("مدت مزیت (روز)"), "21");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.createCampaign).toHaveBeenCalledWith(expect.objectContaining({
    code: "spring-2027",
    name: "Spring 2027",
    kind: "manual_promotion",
    package_code: "training_coach",
    duration_days: 21,
    term_weeks: 4,
  }));
});
