import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError } from "@fitician/core";

import "../../i18n";

const accessApi = vi.hoisted(() => ({
  activateCampaign: vi.fn(),
  adminAccessPackageCodes: ["training", "training_coach", "nutrition", "nutrition_physician", "complete", "complete_care"],
  createCampaign: vi.fn(),
  deactivateCampaign: vi.fn(),
  getCampaigns: vi.fn(),
  updateCampaign: vi.fn(),
}));
vi.mock("./adminAccessApi", () => accessApi);

import { AdminAccessCampaignsPage } from "./AdminAccessCampaignsPage";

const signupBonus = {
  id: "bonus-1",
  code: "autumn-welcome-1405",
  name: "هدیه شروع پاییز",
  description: null,
  kind: "signup_bonus" as const,
  package_code: "complete" as const,
  duration_days: 42,
  term_weeks: 6 as const,
  available_from: "2026-09-22T08:00:00Z",
  available_until: "2026-10-06T08:00:00Z",
  is_active: true,
  max_total_redemptions: 2000,
  public_badge_fa: "هدیه ثبت‌نام",
  public_badge_en: "Signup Gift",
  public_title_fa: "یک دوره کامل تمرین و تغذیه مهمان فیتیشن",
  public_title_en: "Your first complete program is on us",
  public_message_fa: "ثبت‌نام کن و برنامه شخصی خودت را رایگان شروع کن.",
  public_message_en: "Create your account and start your personalized program free.",
  public_cta_fa: "هدیه‌ام رو بگیر",
  public_cta_en: "Claim my gift",
  show_on_landing: true,
  show_on_register: true,
  redemption_count: 0,
  created_by_user_id: null,
  created_at: "2026-09-20T08:00:00Z",
  updated_at: "2026-09-20T08:00:00Z",
};

const redeemedBonus = {
  ...signupBonus,
  id: "bonus-redeemed",
  code: "redeemed-bonus",
  redemption_count: 4,
};

const manual = {
  ...signupBonus,
  id: "manual-1",
  code: "beta-promotion",
  name: "Beta promotion",
  kind: "manual_promotion" as const,
  package_code: "complete_care" as const,
  duration_days: 56,
  term_weeks: 8 as const,
  is_active: false,
  max_total_redemptions: null,
  public_badge_fa: null,
  public_badge_en: null,
  public_title_fa: null,
  public_title_en: null,
  public_message_fa: null,
  public_message_en: null,
  public_cta_fa: null,
  public_cta_en: null,
  show_on_landing: false,
  show_on_register: false,
};

function renderPage() {
  return render(<MemoryRouter><AdminAccessCampaignsPage /></MemoryRouter>);
}

async function openCreate(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "ساخت کمپین" }));
}

async function fillIdentity(user: ReturnType<typeof userEvent.setup>, code = "autumn-2027") {
  await user.type(screen.getByLabelText("کد"), code);
  await user.type(screen.getByLabelText("نام کمپین"), "Autumn 2027");
}

async function chooseSignupBonus(user: ReturnType<typeof userEvent.setup>) {
  await user.selectOptions(screen.getByLabelText("نوع کمپین"), "signup_bonus");
}

beforeEach(() => {
  accessApi.activateCampaign.mockReset();
  accessApi.createCampaign.mockReset();
  accessApi.deactivateCampaign.mockReset();
  accessApi.getCampaigns.mockReset();
  accessApi.updateCampaign.mockReset();
  accessApi.getCampaigns.mockResolvedValue([signupBonus, manual]);
  accessApi.deactivateCampaign.mockResolvedValue({ ...signupBonus, is_active: false });
  accessApi.activateCampaign.mockResolvedValue({ ...manual, is_active: true });
  accessApi.createCampaign.mockResolvedValue(signupBonus);
  accessApi.updateCampaign.mockResolvedValue({ ...redeemedBonus, name: "Updated promotion" });
});

it("lists Signup Bonus and activates or deactivates campaigns without entitlement toggles", async () => {
  const user = userEvent.setup();
  renderPage();

  expect(await screen.findByRole("heading", { name: "کمپین‌ها و هدیه ثبت‌نام" })).toBeInTheDocument();
  expect(screen.getByText("هدیه ثبت‌نام")).toBeInTheDocument();
  expect(screen.getByText("این کمپین فقط هنگام ساخت حساب جدید به کاربر واجد شرایط داده می‌شود.")).toBeInTheDocument();

  const bonusCard = screen.getByTestId("access-campaign-autumn-welcome-1405");
  await user.click(within(bonusCard).getByRole("button", { name: "غیرفعال‌سازی" }));
  expect(accessApi.deactivateCampaign).toHaveBeenCalledWith("bonus-1");

  const manualCard = screen.getByTestId("access-campaign-beta-promotion");
  await user.click(within(manualCard).getByRole("button", { name: "فعال‌سازی" }));
  expect(accessApi.activateCampaign).toHaveBeenCalledWith("manual-1");
});

it.each([4, 6, 8])("creates a Signup Bonus with a %i-week term", async (term) => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await chooseSignupBonus(user);
  await fillIdentity(user, `autumn-${term}`);
  await user.selectOptions(screen.getByLabelText("بسته"), "complete");
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), String(term));
  await user.clear(screen.getByLabelText("مدت مزیت (روز)"));
  await user.type(screen.getByLabelText("مدت مزیت (روز)"), String(term * 7));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.createCampaign).toHaveBeenCalledWith(expect.objectContaining({
    kind: "signup_bonus",
    package_code: "complete",
    duration_days: term * 7,
    term_weeks: term,
    show_on_landing: false,
    show_on_register: false,
  }));
});

it("rejects access duration shorter than the selected training term", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await chooseSignupBonus(user);
  await fillIdentity(user);
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), "6");
  await user.clear(screen.getByLabelText("مدت مزیت (روز)"));
  await user.type(screen.getByLabelText("مدت مزیت (روز)"), "30");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("مدت دسترسی باید حداقل به اندازه مدت تمرین باشد.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("validates required campaign identity before sending", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("کد کمپین الزامی است.")).toBeInTheDocument();
  expect(screen.getByText("نام کمپین الزامی است.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("rejects invalid duration and redemption limits before sending", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await fillIdentity(user);
  await user.clear(screen.getByLabelText("مدت مزیت (روز)"));
  await user.type(screen.getByLabelText("مدت مزیت (روز)"), "3651");
  await user.type(screen.getByLabelText("حداکثر ردیم"), "0");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("مدت مزیت باید بین ۱ تا ۳۶۵۰ روز باشد.")).toBeInTheDocument();
  expect(screen.getByText("حداکثر ردیم باید عددی بزرگ‌تر از صفر باشد.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("keeps the form open and explains an API validation response", async () => {
  const user = userEvent.setup();
  accessApi.createCampaign.mockRejectedValueOnce(new ApiError(422, "Request failed", [
    { loc: ["body", "code"], msg: "String should match pattern" },
  ]));
  renderPage();
  await openCreate(user);
  await fillIdentity(user);
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("کد کمپین معتبر نیست.")).toBeInTheDocument();
  expect(screen.getByRole("alert")).toHaveTextContent("اطلاعات معتبر نیست");
  expect(screen.getByRole("heading", { name: "ساخت کمپین" })).toBeInTheDocument();
});

it("requires a training term when the selected package includes training", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await chooseSignupBonus(user);
  await fillIdentity(user);
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), "");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("برای این بسته، مدت تمرین را انتخاب کنید.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("requires complete bilingual marketing copy when a public surface is enabled", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await chooseSignupBonus(user);
  await fillIdentity(user);
  await user.click(screen.getByLabelText("نمایش در صفحه اصلی"));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByText("برای نمایش عمومی، عنوان، متن و متن دکمه هر دو زبان را کامل کنید.")).toBeInTheDocument();
  expect(accessApi.createCampaign).not.toHaveBeenCalled();
});

it("includes bilingual marketing and surface visibility in the create payload", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await chooseSignupBonus(user);
  await fillIdentity(user);
  await user.click(screen.getByLabelText("نمایش در صفحه اصلی"));
  await user.click(screen.getByLabelText("نمایش هنگام ثبت‌نام"));
  await user.type(screen.getByLabelText("عنوان فارسی"), "عنوان پاییز");
  await user.type(screen.getByLabelText("English title"), "Autumn title");
  await user.type(screen.getByLabelText("متن فارسی"), "پیام پاییز");
  await user.type(screen.getByLabelText("English message"), "Autumn message");
  await user.type(screen.getByLabelText("متن دکمه فارسی"), "شروع کن");
  await user.type(screen.getByLabelText("English CTA"), "Start now");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.createCampaign).toHaveBeenCalledWith(expect.objectContaining({
    public_title_fa: "عنوان پاییز",
    public_title_en: "Autumn title",
    public_message_fa: "پیام پاییز",
    public_message_en: "Autumn message",
    public_cta_fa: "شروع کن",
    public_cta_en: "Start now",
    show_on_landing: true,
    show_on_register: true,
  }));
});

it("keeps manual promotions private and hides public advertising controls", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  expect(screen.queryByLabelText("نمایش در صفحه اصلی")).not.toBeInTheDocument();
  expect(screen.getByText("پروموشن دستی عمومی نیست و در Landing یا صفحه ثبت‌نام نمایش داده نمی‌شود.")).toBeInTheDocument();
  await fillIdentity(user);
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.createCampaign).toHaveBeenCalledWith(expect.objectContaining({
    kind: "manual_promotion",
    show_on_landing: false,
    show_on_register: false,
  }));
});

it("renders Persian and English public previews", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await chooseSignupBonus(user);
  await user.type(screen.getByLabelText("عنوان فارسی"), "پیش‌نمایش فارسی");
  await user.type(screen.getByLabelText("English title"), "English preview");
  await user.type(screen.getByLabelText("متن فارسی"), "پیام فارسی");
  await user.type(screen.getByLabelText("English message"), "English message");

  expect(screen.getByTestId("campaign-preview-rtl")).toHaveTextContent("پیش‌نمایش فارسی");
  expect(screen.getByTestId("campaign-preview-ltr")).toHaveTextContent("English preview");
});

it("locks redeemed semantic fields but keeps marketing editable", async () => {
  const user = userEvent.setup();
  accessApi.getCampaigns.mockResolvedValue([redeemedBonus]);
  renderPage();
  await user.click(within(await screen.findByTestId("access-campaign-redeemed-bonus")).getByRole("button", { name: "ویرایش کمپین" }));

  expect(screen.getByLabelText("نوع کمپین")).toBeDisabled();
  expect(screen.getByLabelText("بسته")).toBeDisabled();
  expect(screen.getByLabelText("مدت مزیت (روز)")).toBeDisabled();
  expect(screen.getByLabelText("مدت تمرین")).toBeDisabled();
  const title = screen.getByLabelText("عنوان فارسی");
  expect(title).not.toBeDisabled();
  await user.clear(title);
  await user.type(title, "عنوان جدید");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.updateCampaign).toHaveBeenCalledWith("bonus-redeemed", expect.objectContaining({
    public_title_fa: "عنوان جدید",
  }));
  expect(accessApi.updateCampaign.mock.calls[0]?.[1]).not.toHaveProperty("package_code");
});

it("surfaces the generic overlap error", async () => {
  const user = userEvent.setup();
  accessApi.activateCampaign.mockRejectedValueOnce(new ApiError(
    409,
    "Signup campaign window overlaps active campaign",
    null,
    "ACCESS_CAMPAIGN_WINDOW_OVERLAPS",
  ));
  renderPage();

  const manualCard = await screen.findByTestId("access-campaign-beta-promotion");
  await user.click(within(manualCard).getByRole("button", { name: "فعال‌سازی" }));

  expect(await screen.findByRole("alert")).toHaveTextContent("این بازه با یک هدیه ثبت‌نام فعال دیگر تداخل دارد.");
});

it("keeps the create action prominent and excludes the legacy package", async () => {
  const user = userEvent.setup();
  renderPage();

  const createButton = await screen.findByRole("button", { name: "ساخت کمپین" });
  expect(createButton).toHaveClass("access-admin-button--create");
  expect(createButton.querySelector(".access-admin-button__icon")).toHaveAttribute("aria-hidden", "true");

  await openCreate(user);
  const packageSelect = screen.getByLabelText("بسته");
  expect(packageSelect.querySelector('option[value="launch_trial"]')).not.toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "انصراف" }));
  await user.click(within(await screen.findByTestId("access-campaign-autumn-welcome-1405")).getByRole("button", { name: "ویرایش کمپین" }));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.updateCampaign).toHaveBeenCalledWith(
    "bonus-1",
    expect.not.objectContaining({ is_active: expect.anything() }),
  );
});

it("warns without blocking specialist packages", async () => {
  const user = userEvent.setup();
  renderPage();
  await openCreate(user);
  await user.selectOptions(screen.getByLabelText("بسته"), "complete_care");

  expect(screen.getByText(/این بسته شامل قابلیت‌های دارای بازبینی انسانی/)).toBeInTheDocument();
});
