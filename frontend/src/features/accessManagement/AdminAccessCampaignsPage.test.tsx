import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "@fitician/core";

import "../../i18n";

const accessApi = vi.hoisted(() => ({
  activateCampaign: vi.fn(),
  adminAccessPackageCodes: ["training", "training_coach", "complete", "complete_care"],
  signupTrialPackageCodes: ["launch_trial"],
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
  available_from: "2026-09-15T08:00:00Z",
  available_until: "2026-10-15T08:00:00Z",
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
  expect(within(launchCard).getByText("شروع کمپین")).toBeInTheDocument();
  expect(within(launchCard).getByText("پایان کمپین")).toBeInTheDocument();
  await user.click(within(launchCard).getByRole("button", { name: "غیرفعال‌سازی" }));

  expect(accessApi.deactivateCampaign).toHaveBeenCalledWith("launch-1");
});

it.each([4, 6, 8])("creates a package campaign with a %i-week term", async (term) => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  await user.type(screen.getByLabelText("کد"), "spring-2027");
  await user.type(screen.getByLabelText("نام کمپین"), "Spring 2027");
  await user.selectOptions(screen.getByLabelText("بسته"), "training_coach");
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), String(term));
  await user.clear(screen.getByLabelText("مدت مزیت (روز)"));
  await user.type(screen.getByLabelText("مدت مزیت (روز)"), "21");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.createCampaign).toHaveBeenCalledWith(expect.objectContaining({
    code: "spring-2027",
    name: "Spring 2027",
    kind: "manual_promotion",
    package_code: "training_coach",
    duration_days: 21,
    term_weeks: term,
  }));
});

it("validates required campaign fields before sending a request", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("کد کمپین الزامی است.")).toBeInTheDocument();
  expect(screen.getByText("نام کمپین الزامی است.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
  expect(screen.getByRole("button", { name: "ذخیره تغییرات" })).toBeInTheDocument();
});

it("requires a training term when the selected package includes training", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  await user.type(screen.getByLabelText("کد"), "spring-2027");
  await user.type(screen.getByLabelText("نام کمپین"), "Spring 2027");
  await user.selectOptions(screen.getByLabelText("بسته"), "training_coach");
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), "");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("برای این بسته، مدت تمرین را انتخاب کنید.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("rejects invalid benefit duration and redemption limits before sending", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  await user.type(screen.getByLabelText("کد"), "spring-2027");
  await user.type(screen.getByLabelText("نام کمپین"), "Spring 2027");
  await user.clear(screen.getByLabelText("مدت مزیت (روز)"));
  await user.type(screen.getByLabelText("مدت مزیت (روز)"), "0");
  await user.type(screen.getByLabelText("حداکثر ردیم"), "0");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("مدت مزیت باید بین ۱ تا ۳۶۵۰ روز باشد.")).toBeInTheDocument();
  expect(screen.getByText("حداکثر ردیم باید عددی بزرگ‌تر از صفر باشد.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("keeps the form open and explains a validation response from the API", async () => {
  const user = userEvent.setup();
  accessApi.createCampaign.mockRejectedValueOnce(new ApiError(422, "Request failed", [
    { loc: ["body", "code"], msg: "String should match pattern" },
  ]));
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  await user.type(screen.getByLabelText("کد"), "spring-2027");
  await user.type(screen.getByLabelText("نام کمپین"), "Spring 2027");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("کد کمپین معتبر نیست.")).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("اطلاعات فرم را اصلاح کنید.");
  expect(screen.getByRole("heading", { name: "ساخت کمپین" })).toBeInTheDocument();
});

it("shows the activation conflict instead of a generic load error", async () => {
  const user = userEvent.setup();
  accessApi.activateCampaign.mockRejectedValueOnce(new ApiError(
    409,
    "Signup campaign window overlaps active campaign",
    null,
    "ACCESS_CAMPAIGN_WINDOW_OVERLAPS",
  ));
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  const manualCard = await screen.findByTestId("access-campaign-beta-promotion");
  await user.click(within(manualCard).getByRole("button", { name: "فعال‌سازی" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("این بازه با یک Signup Trial فعال دیگر تداخل دارد.");
  expect(screen.queryByText("اطلاعات دسترسی دریافت نشد.")).not.toBeInTheDocument();
});

it("makes the create campaign action visually prominent", async () => {
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  const createButton = await screen.findByRole("button", { name: "ساخت کمپین" });

  expect(createButton).toHaveClass("access-admin-button--create");
  expect(createButton.querySelector(".access-admin-button__icon")).toHaveAttribute("aria-hidden", "true");
});

it("limits campaign packages by kind and keeps activation out of edit updates", async () => {
  const user = userEvent.setup();
  render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);

  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
  const packageSelect = screen.getByLabelText("بسته");
  expect(within(packageSelect).queryByRole("option", { name: "دوره آزمایشی شروع" })).not.toBeInTheDocument();

  await user.selectOptions(screen.getByLabelText("نوع کمپین"), "signup_trial");
  expect(packageSelect).toHaveValue("launch_trial");
  expect(within(packageSelect).getAllByRole("option")).toHaveLength(1);
  const termSelect = screen.getByLabelText("مدت تمرین");
  expect(termSelect).toHaveValue("4");
  expect(termSelect).toBeDisabled();

  await user.click(screen.getByRole("button", { name: "انصراف" }));
  const launchCard = screen.getByTestId("access-campaign-launch_trial_v1");
  await user.click(within(launchCard).getByRole("button", { name: "ویرایش کمپین" }));
  expect(screen.queryByRole("checkbox", { name: "فعال" })).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.updateCampaign).toHaveBeenCalledWith(
    "launch-1",
    expect.not.objectContaining({ is_active: expect.anything() }),
  );
});
