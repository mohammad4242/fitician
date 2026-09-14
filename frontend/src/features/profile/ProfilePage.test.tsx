import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { TransportError } from "@fitician/core";

import i18n from "../../i18n";
import type { ProductMode, Profile, SharedProfile } from "./types";

const context = vi.hoisted(() => ({
  profile: null as Profile | null,
  productMode: "both" as ProductMode,
  updateProfile: vi.fn(),
}));

const profileApi = vi.hoisted(() => ({
  getSharedProfile: vi.fn(),
  saveSharedProfile: vi.fn(),
}));

vi.mock("./api", () => profileApi);
vi.mock("../auth/AuthContext", () => ({ useAuth: () => ({ user: { email: "member@example.com" } }) }));

vi.mock("../nutrition/NutritionOnboardingFlow", () => ({
  NutritionOnboardingFlow: ({ onBack }: { onBack?: () => void }) => (
    <section aria-label="اطلاعات تغذیه‌ای">
      <h2>اطلاعات تغذیه‌ای</h2>
      <p>فرم یکپارچه تغذیه</p>
      <button type="button" onClick={onBack}>بازگشت</button>
    </section>
  ),
}));

vi.mock("./ProfileContext", () => ({
  useProfile: () => ({
    profile: context.profile,
    productMode: context.productMode,
    status: "ready",
    retryProfile: vi.fn(),
    createProfile: vi.fn(),
    updateProfile: context.updateProfile,
  }),
  useOptionalProfile: () => ({
    status: "ready",
  }),
}));

import { ProfilePage } from "./ProfilePage";

const savedProfile: Profile = {
  user_id: "018f0000-0000-7000-8000-000000000001",
  display_name: "Mohammad",
  birth_date: "2000-05-14",
  sex: "male",
  height_cm: 178,
  current_weight_kg: 76.5,
  weight_measured_at: "2026-07-27T12:00:00Z",
  shoulder_circumference_cm: null,
  waist_circumference_cm: null,
  hip_circumference_cm: null,
  circumferences_measured_at: null,
  fitness_goal: "build_muscle",
  experience_level: "beginner",
  training_days_per_week: 3,
  training_location: "home",
  home_training_setup: "dumbbells_available",
  available_equipment: ["bodyweight", "dumbbell", "pull_up_bar"],
  priority_muscles: ["chest"],
  session_duration_minutes: 75,
  training_intensity: "moderate",
  physical_limitations: "Knee pain",
  training_cautions: ["knee"],
  plan_duration_weeks: 6,
  created_at: "2026-07-27T12:00:00Z",
  updated_at: "2026-07-27T12:00:00Z",
};

const savedSharedProfile: SharedProfile = {
  user_id: savedProfile.user_id,
  product_mode: "nutrition",
  display_name: savedProfile.display_name,
  birth_date: savedProfile.birth_date,
  sex: savedProfile.sex,
  height_cm: savedProfile.height_cm,
  current_weight_kg: savedProfile.current_weight_kg,
  fitness_goal: savedProfile.fitness_goal,
  weight_measured_at: savedProfile.weight_measured_at,
};

function Destination() {
  const location = useLocation();
  return <h1>{`destination:${location.pathname}`}</h1>;
}

function renderProfilePage(initialEntry = "/profile") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/dashboard" element={<Destination />} />
        <Route path="/login" element={<Destination />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function openTrainingPage(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "بعدی" }));
  expect(screen.getByRole("heading", { name: "اطلاعات تمرینی" })).toBeInTheDocument();
}

beforeEach(async () => {
  vi.clearAllMocks();
  context.profile = savedProfile;
  context.productMode = "both";
  profileApi.getSharedProfile.mockResolvedValue(savedSharedProfile);
  profileApi.saveSharedProfile.mockResolvedValue(savedSharedProfile);
  await i18n.changeLanguage("fa");
});

afterEach(() => {
  vi.unstubAllEnvs();
});

it("shows signed-in profile information as three ordered full pages", async () => {
  const user = userEvent.setup();
  renderProfilePage();

  expect(screen.getByRole("heading", { name: "اطلاعات شخصی" })).toBeInTheDocument();
  expect(screen.getByRole("form", { name: "اطلاعات شخصی" })).toBeInTheDocument();
  expect(screen.getByText("مرحله ۱ از ۳")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "بعدی" }));
  expect(screen.getByRole("heading", { name: "اطلاعات تمرینی" })).toBeInTheDocument();
  expect(screen.getByText("مرحله ۲ از ۳")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "بعدی" }));
  expect(screen.getByRole("heading", { name: "اطلاعات تغذیه‌ای" })).toBeInTheDocument();
  expect(screen.getByText("مرحله ۳ از ۳")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "بازگشت" }));
  expect(screen.getByRole("heading", { name: "اطلاعات تمرینی" })).toBeInTheDocument();
});

it("leads with a compact real-data account summary and edit action", () => {
  renderProfilePage();

  const summary = screen.getByRole("region", { name: "خلاصه پروفایل" });
  expect(summary).toHaveTextContent("Mohammad");
  expect(summary).toHaveTextContent("۱۷۸");
  expect(summary).toHaveTextContent("۷۶٫۵");
  expect(screen.getByRole("link", { name: "ویرایش پروفایل" })).toHaveAttribute("href", "#profile-editor");
});

it("returns from the first profile page to the dashboard", async () => {
  const user = userEvent.setup();
  renderProfilePage();

  await user.click(screen.getByRole("button", { name: "بازگشت" }));

  expect(screen.getByRole("heading", { name: "destination:/dashboard" })).toBeInTheDocument();
});

it("keeps training optional for nutrition-only members and continues to nutrition", async () => {
  context.profile = null;
  context.productMode = "nutrition";
  const user = userEvent.setup();
  renderProfilePage();

  expect(await screen.findByRole("heading", { name: "اطلاعات شخصی" })).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "بعدی" }));

  expect(screen.getByRole("heading", { name: "اطلاعات تمرینی" })).toBeInTheDocument();
  expect(screen.getByText("این بخش برای مسیر تغذیه اختیاری است.")).toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "بعدی" }));

  expect(screen.getByRole("heading", { name: "اطلاعات تغذیه‌ای" })).toBeInTheDocument();
});

it("uses English labels and left-to-right layout for every signed-in profile page", async () => {
  await i18n.changeLanguage("en");
  const user = userEvent.setup();
  renderProfilePage();

  const heading = screen.getByRole("heading", { name: "Personal information" });
  expect(heading.closest(".profile-page-shell")).toHaveAttribute("dir", "ltr");
  expect(screen.getByText("Step 1 of 3")).toBeInTheDocument();

  await user.click(screen.getByRole("button", { name: "Next" }));
  expect(screen.getByRole("heading", { name: "Training information" })).toBeInTheDocument();
  expect(screen.getByText("Step 2 of 3")).toBeInTheDocument();
});

it("renders every saved profile value in its editable profile page", async () => {
  const user = userEvent.setup();
  renderProfilePage();

  expect(screen.getByLabelText("نام نمایشی")).toHaveValue("Mohammad");
  expect(screen.getByRole("button", { name: "تاریخ تولد" })).toHaveTextContent("۲۵ اردیبهشت ۱۳۷۹");
  expect(screen.getByLabelText("جنسیت")).toHaveValue("male");
  expect(screen.getByLabelText("قد (سانتی‌متر)")).toHaveValue(178);
  expect(screen.getByLabelText("وزن فعلی (کیلوگرم)")).toHaveValue(76.5);
  expect(screen.getByLabelText("هدف ورزشی")).toHaveValue("build_muscle");
  expect(screen.getByRole("option", { name: "افزایش قدرت" })).toHaveValue("strength");

  await openTrainingPage(user);
  expect(screen.getByLabelText("سطح تجربه")).toHaveValue("beginner");
  expect(screen.getByLabelText("روزهای تمرین در هفته")).toHaveValue(3);
  expect(screen.getByLabelText("کجا تمرین می‌کنی؟")).toHaveValue("home");
  expect(screen.getByRole("group", { name: "برای تمرین در خانه چه امکاناتی داری؟" })).toBeInTheDocument();
  const homeGroup = screen.getByRole("group", { name: "برای تمرین در خانه چه امکاناتی داری؟" });
  expect(within(homeGroup).getByRole("radio", { name: "وزن بدن" })).not.toBeChecked();
  expect(within(homeGroup).getByRole("radio", { name: "دمبل" })).toBeChecked();
  expect(within(homeGroup).getByRole("radio", { name: "کش" })).not.toBeChecked();
  expect(within(homeGroup).getByRole("radio", { name: "دمبل + کش" })).not.toBeChecked();
  expect(within(homeGroup).queryByLabelText("میله بارفیکس")).not.toBeInTheDocument();
  expect(within(homeGroup).queryByLabelText("نیمکت")).not.toBeInTheDocument();
  expect(screen.getByLabelText("معمولاً برای هر جلسه چقدر زمان داری؟")).toHaveValue(
    "75",
  );
  expect(screen.getByLabelText("شدت معمول تمرین")).toHaveValue("moderate");
  expect(screen.getByLabelText("سینه")).toBeChecked();
  expect(screen.queryByLabelText("بالاتنه")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("محدودیت‌های جسمی (اختیاری)")).not.toBeInTheDocument();
});

it("keeps an existing custom weekday selection on profile load", async () => {
  context.profile = {
    ...savedProfile,
    training_days_per_week: 4,
    preferred_weekdays: [0, 2, 4, 6],
  };
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);

  expect(screen.getByRole("group", { name: "روزهای دلخواه" })).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: "شنبه" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "دوشنبه" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "چهارشنبه" })).toBeChecked();
  expect(screen.getByRole("checkbox", { name: "جمعه" })).toBeChecked();
  expect(context.updateProfile).not.toHaveBeenCalled();
});

it("shows the actual count when a legacy empty calendar opens custom selection", async () => {
  context.profile = {
    ...savedProfile,
    training_days_per_week: 4,
    preferred_weekdays: [],
  };
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);
  const weekdayGroup = screen.getByRole("radiogroup", { name: "روزهای تمرینت" });
  await user.click(within(weekdayGroup).getByRole("radio", { name: "روزهای تمرین را خودم انتخاب می‌کنم" }));

  expect(screen.getByText("۰ از ۴ روز انتخاب شده")).toBeInTheDocument();
  const grid = screen.getByRole("group", { name: "روزهای دلخواه" });
  expect(within(grid).queryAllByRole("checkbox", { checked: true })).toHaveLength(0);
});

it("marks an existing second weekday preset as selected on profile load", async () => {
  context.profile = {
    ...savedProfile,
    training_days_per_week: 4,
    preferred_weekdays: [1, 2, 4, 5],
  };
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);

  const weekdayGroup = screen.getByRole("radiogroup", { name: "روزهای تمرینت" });
  expect(within(weekdayGroup).getByRole("radio", { name: "یکشنبه · دوشنبه · چهارشنبه · پنجشنبه" })).toHaveAttribute(
    "aria-checked",
    "true",
  );
  expect(within(weekdayGroup).getByRole("radio", { name: "شنبه · یکشنبه · سه‌شنبه · چهارشنبه" })).toHaveAttribute(
    "aria-checked",
    "false",
  );
});

it("keeps profile focus single-select and patches only the replacement focus", async () => {
  const user = userEvent.setup();
  context.updateProfile.mockResolvedValue({ ...savedProfile, priority_muscles: ["biceps"] });
  renderProfilePage();

  await openTrainingPage(user);
  await user.click(screen.getByLabelText("جلو بازو"));
  expect(screen.getByLabelText("جلو بازو")).toBeChecked();
  expect(screen.getByLabelText("سینه")).not.toBeChecked();
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  await waitFor(() => expect(context.updateProfile).toHaveBeenCalledWith({ priority_muscles: ["biceps"] }));
});

it("uses the supplied training still in the profile header", () => {
  renderProfilePage();

  const background = screen.getByTestId("member-header-image");
  expect(background).toHaveAttribute(
    "src",
    expect.stringContaining("auth-training-accent"),
  );
  expect(background.parentElement).toHaveClass("member-page-background");
});

it("shows the latest measured weight and localized measurement time", () => {
  vi.stubEnv("TZ", "UTC");
  context.profile = {
    ...savedProfile,
    weight_measured_at: "2026-09-13T20:45:00Z",
  };
  renderProfilePage();
  const expectedWeight = new Intl.NumberFormat("fa-IR", {
    maximumFractionDigits: 2,
  }).format(context.profile.current_weight_kg);

  expect(screen.getAllByText(`${expectedWeight} کیلوگرم`)).toHaveLength(2);
  expect(screen.getByText("ثبت‌شده در ۲۳ شهریور ۱۴۰۵، ۰:۱۵")).toBeInTheDocument();
});

it("offers optional body-photo progress from the profile without blocking edits", () => {
  renderProfilePage();

  expect(screen.getByRole("link", { name: "شروع جلسه عکس" })).toHaveAttribute(
    "href",
    "/body-progress",
  );
  expect(screen.getByText(/اختیاری — برای برنامه تمرینی دقیق‌تر/)).toBeInTheDocument();
});

it("skips profile update when no values changed", async () => {
  const user = userEvent.setup();
  renderProfilePage();

  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(context.updateProfile).not.toHaveBeenCalled();
  expect(screen.getByRole("status")).toHaveTextContent("تغییری برای ذخیره نیست");
});

it("sends only a changed display name", async () => {
  context.updateProfile.mockResolvedValue({
    ...savedProfile,
    display_name: "New Name",
  });
  const user = userEvent.setup();
  renderProfilePage();

  await user.clear(screen.getByLabelText("نام نمایشی"));
  await user.type(screen.getByLabelText("نام نمایشی"), "New Name");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  await waitFor(() =>
    expect(context.updateProfile).toHaveBeenCalledWith({
      display_name: "New Name",
    }),
  );
});

it("saves only fields from the active profile page", async () => {
  context.updateProfile.mockResolvedValue({ ...savedProfile, display_name: "New Name" });
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);
  await user.selectOptions(screen.getByLabelText("کجا تمرین می‌کنی؟"), "gym");
  await user.click(screen.getByRole("button", { name: "بازگشت" }));
  await user.clear(screen.getByLabelText("نام نمایشی"));
  await user.type(screen.getByLabelText("نام نمایشی"), "New Name");
  await user.click(screen.getByRole("button", { name: "بعدی" }));

  await waitFor(() => expect(context.updateProfile).toHaveBeenCalledWith({ display_name: "New Name" }));
});

it("sends only a changed current weight", async () => {
  context.updateProfile.mockResolvedValue({
    ...savedProfile,
    current_weight_kg: 75.25,
    weight_measured_at: "2026-07-28T12:00:00Z",
  });
  const user = userEvent.setup();
  renderProfilePage();

  await user.clear(screen.getByLabelText("وزن فعلی (کیلوگرم)"));
  await user.type(screen.getByLabelText("وزن فعلی (کیلوگرم)"), "75.25");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  await waitFor(() =>
    expect(context.updateProfile).toHaveBeenCalledWith({
      current_weight_kg: 75.25,
    }),
  );
});

it("does not expose or patch legacy free-text limitations", async () => {
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);
  expect(screen.queryByLabelText("محدودیت‌های جسمی (اختیاری)")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(context.updateProfile).not.toHaveBeenCalled();
});

it("updates the selected home preset and canonical inventory", async () => {
  context.updateProfile.mockResolvedValue({
    ...savedProfile,
    available_equipment: ["bodyweight", "resistance_band", "pull_up_bar"],
    home_training_setup: "resistance_bands_available",
  });
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);
  await user.click(screen.getByRole("radio", { name: "کش" }));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  await waitFor(() =>
    expect(context.updateProfile).toHaveBeenCalledWith({
      home_training_setup: "resistance_bands_available",
      available_equipment: ["bodyweight", "resistance_band", "pull_up_bar"],
    }),
  );
});

it("does not carry a gym inventory into home training", async () => {
  context.profile = {
    ...savedProfile,
    training_location: "gym",
    home_training_setup: null,
    available_equipment: ["bodyweight", "dumbbell", "barbell", "cable", "machine"],
  };
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);
  await user.selectOptions(screen.getByLabelText("کجا تمرین می‌کنی؟"), "home");

  const homeGroup = screen.getByRole("group", { name: "برای تمرین در خانه چه امکاناتی داری؟" });
  expect(within(homeGroup).getByRole("radio", { name: "وزن بدن" })).not.toBeChecked();
  expect(within(homeGroup).getByRole("radio", { name: "دمبل" })).not.toBeChecked();
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));
  expect(screen.getByText("این فیلد الزامی است.")).toBeInTheDocument();
  expect(context.updateProfile).not.toHaveBeenCalled();
});

it("clears home setup and serializes the workout preference edit", async () => {
  context.updateProfile.mockResolvedValue({
    ...savedProfile,
    training_location: "gym",
    home_training_setup: null,
    available_equipment: null,
    session_duration_minutes: 90,
  });
  const user = userEvent.setup();
  renderProfilePage();

  await openTrainingPage(user);
  await user.selectOptions(screen.getByLabelText("کجا تمرین می‌کنی؟"), "gym");
  expect(
    screen.queryByLabelText("برای تمرین در خانه چه امکاناتی داری؟"),
  ).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("معمولاً برای هر جلسه چقدر زمان داری؟"), "90");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  await waitFor(() =>
    expect(context.updateProfile).toHaveBeenCalledWith({
      training_location: "gym",
      home_training_setup: null,
      available_equipment: null,
      session_duration_minutes: 90,
    }),
  );
});

it("focuses the first invalid edit and skips profile update", async () => {
  const user = userEvent.setup();
  renderProfilePage();

  await user.clear(screen.getByLabelText("نام نمایشی"));
  await user.clear(screen.getByLabelText("قد (سانتی‌متر)"));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(screen.getByLabelText("نام نمایشی")).toHaveFocus();
  expect(context.updateProfile).not.toHaveBeenCalled();
});

it("shows success from the returned profile and resets the patch baseline", async () => {
  context.updateProfile.mockResolvedValue({
    ...savedProfile,
    display_name: "New Name",
  });
  const user = userEvent.setup();
  renderProfilePage();

  await user.clear(screen.getByLabelText("نام نمایشی"));
  await user.type(screen.getByLabelText("نام نمایشی"), "New Name");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByRole("status")).toHaveTextContent(
    "پروفایل New Name ذخیره شد",
  );
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));
  expect(context.updateProfile).toHaveBeenCalledOnce();
});

it("keeps edited values and shows an alert when profile update fails", async () => {
  context.updateProfile.mockRejectedValue(new TransportError("offline"));
  const user = userEvent.setup();
  renderProfilePage();

  await user.clear(screen.getByLabelText("نام نمایشی"));
  await user.type(screen.getByLabelText("نام نمایشی"), "Offline Name");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "اتصال اینترنت در دسترس نیست",
  );
  expect(screen.getByLabelText("نام نمایشی")).toHaveValue("Offline Name");
});
