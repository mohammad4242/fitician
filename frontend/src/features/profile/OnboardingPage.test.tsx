import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  MemoryRouter,
  Route,
  Routes,
  useLocation,
  useNavigationType,
} from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import { ApiError, TransportError } from "@fitician/core";

import i18n from "../../i18n";
import type { SafetyProfileInput } from "../nutrition/types";
import {
  PENDING_NUTRITION_BASICS_KEY,
  type OnboardingDraft,
  type PreAccountNutritionBasics,
} from "../publicOnboarding/onboardingDraft";
import type { Profile } from "./types";

const profileContext = vi.hoisted(() => ({
  status: "mode_selected" as "missing" | "mode_selected",
  productMode: "training" as "training" | "nutrition" | "both" | null,
  createProfile: vi.fn(),
  selectProductMode: vi.fn(),
  retryProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

const authContext = vi.hoisted(() => ({
  logout: vi.fn(),
}));

const nutritionFlow = vi.hoisted(() => ({ props: null as unknown }));

vi.mock("./ProfileContext", () => ({
  useProfile: () => ({
    profile: null,
    ...profileContext,
  }),
  useOptionalProfile: () => ({ status: "ready" }),
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => authContext,
}));

vi.mock("../nutrition/NutritionOnboardingFlow", () => ({
  NutritionOnboardingFlow: (props: unknown) => {
    nutritionFlow.props = props;
    return <h1>Nutrition flow</h1>;
  },
}));

import { OnboardingPage } from "./OnboardingPage";

const createdProfile: Profile = {
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
  training_location: "gym",
  home_training_setup: null,
  available_equipment: [],
  session_duration_minutes: 60,
  training_intensity: "moderate",
  physical_limitations: null,
  training_cautions: [],
  plan_duration_weeks: 4,
  created_at: "2026-07-27T12:00:00Z",
  updated_at: "2026-07-27T12:00:00Z",
};

function Destination() {
  const location = useLocation();
  const navigationType = useNavigationType();
  return <h1>{navigationType + ":" + location.pathname}</h1>;
}

function renderOnboarding() {
  return render(
    <MemoryRouter initialEntries={["/onboarding"]}>
      <Routes>
        <Route path="/onboarding" element={<OnboardingPage />} />
        <Route path="/dashboard" element={<Destination />} />
        <Route path="/body-progress/new" element={<Destination />} />
        <Route path="/" element={<Destination />} />
      </Routes>
    </MemoryRouter>,
  );
}

async function choosePersianBirthDate(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: "تاریخ تولد" }));
  await user.selectOptions(screen.getByRole("combobox", { name: "تاریخ تولد - روز" }), "25");
  await user.selectOptions(screen.getByRole("combobox", { name: "تاریخ تولد - ماه" }), "2");
  await user.selectOptions(screen.getByRole("combobox", { name: "تاریخ تولد - سال" }), "1379");
  await user.click(screen.getByRole("button", { name: "انتخاب" }));
}

async function completeSharedQuestions(
  user: ReturnType<typeof userEvent.setup>,
  displayName = "  Mohammad  ",
) {
  await user.type(screen.getByLabelText("نام نمایشی"), displayName);
  await user.click(screen.getByRole("button", { name: "ادامه" }));
  await choosePersianBirthDate(user);
  await user.click(screen.getByRole("button", { name: "ادامه" }));
  await user.click(screen.getByRole("button", { name: "مرد" }));
  await user.type(await screen.findByLabelText("قد (سانتی‌متر)"), "178");
  await user.type(screen.getByLabelText("وزن فعلی (کیلوگرم)"), "76.5");
  await user.click(screen.getByRole("button", { name: "ادامه" }));
  await user.click(await screen.findByRole("button", { name: "عضله‌سازی 💪" }));
  expect(
    await screen.findByRole("heading", { name: "چقدر سابقه تمرین مداوم داری؟" }),
  ).toBeInTheDocument();
}

async function completeTrainingQuestions(
  user: ReturnType<typeof userEvent.setup>,
  location: "باشگاه" | "خانه" = "باشگاه",
) {
  await user.click(screen.getByRole("button", { name: "مبتدی (زیر ۶ ماه)" }));
  await user.click(await screen.findByRole("button", { name: "ادامه" }));
  await user.click(await screen.findByRole("button", { name: "۳ روز در هفته" }));
  await user.click(await screen.findByRole("button", { name: location }));
  if (location === "خانه") {
    expect(
      await screen.findByRole("heading", { name: "در خانه چه امکاناتی داری؟" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "دمبل + کش" }));
  }
  await user.click(await screen.findByRole("button", { name: "۶۰ دقیقه" }));
  await user.click(await screen.findByRole("button", { name: "متوسط" }));
  await user.click(
    await screen.findByRole("button", { name: "تمرکز ویژه‌ای ندارم" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "رد کردن این سؤال" }),
  );
  await user.click(await screen.findByRole("button", { name: "۴ هفته" }));
}

beforeEach(async () => {
  vi.clearAllMocks();
  sessionStorage.clear();
  nutritionFlow.props = null;
  authContext.logout.mockResolvedValue(undefined);
  profileContext.status = "mode_selected";
  profileContext.productMode = "training";
  await i18n.changeLanguage("fa");
});

it("renders authenticated onboarding in the public presentation shell", () => {
  const { container } = renderOnboarding();

  const onboarding = container.querySelector("main.public-onboarding.authenticated-onboarding");
  expect(onboarding?.querySelector(".public-onboarding__header")).toBeInTheDocument();
  expect(onboarding?.querySelector(".public-onboarding__stage")).toBeInTheDocument();
  expect(container.querySelector(".auth-shell")).not.toBeInTheDocument();
  expect(container.querySelector(".form-wrap")).not.toBeInTheDocument();
  expect(screen.getByTestId("authenticated-onboarding-brand-logo")).toHaveClass(
    "fitician-brand-logo",
  );
});

it("uses the public mode cards and keeps product selection behavior", async () => {
  profileContext.status = "missing";
  profileContext.productMode = null;
  profileContext.selectProductMode.mockResolvedValue({
    user_id: createdProfile.user_id,
    product_mode: "both",
    completion_state: "shared_profile_incomplete",
  });
  const user = userEvent.setup();
  const { container } = renderOnboarding();

  const expectedModes = [
    ["برنامه تمرینی", "training"],
    ["برنامه تغذیه", "nutrition"],
    ["تمرین و تغذیه", "both"],
  ] as const;
  for (const [label, mode] of expectedModes) {
    const card = screen.getByRole("button", { name: label });
    expect(card).toHaveClass("product-mode-card", "mode-" + mode);
    expect(card.querySelector(".product-mode-card__icon")).toBeInTheDocument();
    expect(card.querySelector(".product-mode-card__content")).toBeInTheDocument();
  }
  const bothCard = screen.getByRole("button", { name: "تمرین و تغذیه" });
  expect(bothCard).toHaveClass("is-recommended");
  expect(bothCard.querySelector(".product-mode-card__badge")).toHaveTextContent(
    "پیشنهاد فیتیشن",
  );
  expect(container.querySelector(".auth-shell")).not.toBeInTheDocument();

  for (const [label, mode] of expectedModes) {
    await user.click(screen.getByRole("button", { name: label }));
    await waitFor(() =>
      expect(profileContext.selectProductMode).toHaveBeenLastCalledWith(mode),
    );
  }
});

it("preserves safe error presentation when selecting a product mode fails", async () => {
  profileContext.status = "missing";
  profileContext.productMode = null;
  profileContext.selectProductMode.mockRejectedValueOnce(
    new ApiError(503, "private mode detail", null, "SERVICE_UNAVAILABLE", {
      requestId: "onboarding-mode-request-1",
    }),
  );
  const user = userEvent.setup();
  renderOnboarding();

  await user.click(screen.getByRole("button", { name: "تمرین و تغذیه" }));

  const alert = await screen.findByRole("alert");
  expect(alert).toHaveTextContent("سرویس موقتاً در دسترس نیست");
  expect(alert).not.toHaveTextContent("private mode detail");
  expect(alert).not.toHaveTextContent("onboarding-mode-request-1");
});

it("starts authenticated training with the guided shared-profile question", () => {
  renderOnboarding();

  expect(
    screen.getByRole("heading", { name: "دوست داری چه صدایت کنیم؟" }),
  ).toBeInTheDocument();
  expect(
    screen.queryByRole("heading", { name: "پروفایل ورزشی‌ات را بساز" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("نام نمایشی")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "بازگشت" })).not.toBeInTheDocument();
});

it("moves from shared questions into the public guided training sequence", async () => {
  const user = userEvent.setup();
  renderOnboarding();

  await completeSharedQuestions(user);

  expect(
    screen.getByRole("heading", { name: "چقدر سابقه تمرین مداوم داری؟" }),
  ).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "مبتدی (زیر ۶ ماه)" })).toBeInTheDocument();
});

it("creates the normalized profile and replaces the route after guided training", async () => {
  profileContext.createProfile.mockResolvedValue(createdProfile);
  const user = userEvent.setup();
  renderOnboarding();

  await completeSharedQuestions(user);
  await completeTrainingQuestions(user);

  await waitFor(() => expect(profileContext.createProfile).toHaveBeenCalledOnce());
  expect(profileContext.createProfile).toHaveBeenCalledWith({
    display_name: "Mohammad",
    birth_date: "2000-05-14",
    sex: "male",
    height_cm: 178,
    current_weight_kg: 76.5,
    shoulder_circumference_cm: null,
    waist_circumference_cm: null,
    hip_circumference_cm: null,
    fitness_goal: "build_muscle",
    experience_level: "beginner",
    training_age_months: null,
    training_days_per_week: 3,
    preferred_weekdays: null,
    priority_muscles: null,
    training_location: "gym",
    home_training_setup: null,
    available_equipment: null,
    session_duration_minutes: 60,
    training_intensity: "moderate",
    training_cautions: [],
    plan_duration_weeks: 4,
  });
  expect(
    await screen.findByRole("heading", { name: "REPLACE:/body-progress/new" }),
  ).toBeInTheDocument();
});

it("keeps guided home setup and equipment in the created profile", async () => {
  profileContext.createProfile.mockResolvedValue(createdProfile);
  const user = userEvent.setup();
  renderOnboarding();

  await completeSharedQuestions(user);
  await completeTrainingQuestions(user, "خانه");

  await waitFor(() => expect(profileContext.createProfile).toHaveBeenCalledOnce());
  expect(profileContext.createProfile).toHaveBeenCalledWith(
    expect.objectContaining({
      training_location: "home",
      home_training_setup: "dumbbells_and_resistance_bands_available",
      available_equipment: ["bodyweight", "dumbbell", "resistance_band", "pull_up_bar"],
    }),
  );
});

it("keeps the guided training question visible and shows the existing error after creation fails", async () => {
  profileContext.createProfile.mockRejectedValue(new TransportError("offline"));
  const user = userEvent.setup();
  renderOnboarding();

  await completeSharedQuestions(user);
  await completeTrainingQuestions(user);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "اتصال اینترنت در دسترس نیست",
  );
  expect(
    screen.getByRole("heading", { name: "این برنامه چند هفته باشد؟" }),
  ).toBeInTheDocument();
  expect(profileContext.createProfile).toHaveBeenCalledOnce();
});

it("logs out from authenticated onboarding and returns to the public landing", async () => {
  const user = userEvent.setup();
  renderOnboarding();

  await user.click(screen.getByRole("button", { name: "خروج" }));

  expect(authContext.logout).toHaveBeenCalledOnce();
  expect(await screen.findByRole("heading", { name: "REPLACE:/" })).toBeInTheDocument();
});

it("keeps the safe error notice when logout fails", async () => {
  authContext.logout.mockRejectedValueOnce(new TransportError("offline"));
  const user = userEvent.setup();
  renderOnboarding();

  await user.click(screen.getByRole("button", { name: "خروج" }));

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "اتصال اینترنت در دسترس نیست",
  );
});

it("resumes pending nutrition data within the authenticated presentation shell", () => {
  const safety: SafetyProfileInput = {
    conditions: [{ code: "type_2_diabetes_non_insulin", details: null }],
    medications: [],
    dangerous_food_reaction_history: false,
    pregnant: true,
    breastfeeding: false,
    eating_disorder_diagnosed: false,
    eating_disorder_active_symptoms: false,
    emergency_or_danger_symptoms: false,
    complex_medication_food_interaction: false,
    physician_dietary_restrictions: null,
    other_relevant_condition: null,
  };
  const nutritionBasics: PreAccountNutritionBasics = {
    daily_activity_level: "moderate",
    individual_monthly_food_budget_irr: 8_000_000,
    budget_style: "flexible",
    plan_style: "balanced",
    allergies: [],
    intolerances: [],
    dietary_pattern: "omnivore",
  };
  sessionStorage.setItem(
    PENDING_NUTRITION_BASICS_KEY,
    JSON.stringify({ safety, nutritionBasics }),
  );
  profileContext.productMode = "nutrition";
  const { container } = renderOnboarding();

  expect(screen.getByRole("heading", { name: "Nutrition flow" })).toBeInTheDocument();
  expect(container.querySelector("main.public-onboarding.authenticated-onboarding"))
    .toBeInTheDocument();
  const props = nutritionFlow.props as {
    productMode: string;
    trainingProfileExists: boolean;
    initialDraft?: OnboardingDraft;
    initialNutritionBasics?: PreAccountNutritionBasics;
    onCreateTrainingProfile: unknown;
    onComplete: unknown;
    onNutritionComplete: unknown;
    editExisting: boolean;
  };
  expect(props).toMatchObject({
    productMode: "nutrition",
    trainingProfileExists: false,
    editExisting: true,
  });
  expect(props.initialDraft).toMatchObject({ mode: "nutrition", safety });
  expect(props.initialNutritionBasics).toEqual(nutritionBasics);
  expect(props.onCreateTrainingProfile).toBe(profileContext.createProfile);
  expect(props.onComplete).toBe(profileContext.retryProfile);
  expect(props.onNutritionComplete).toEqual(expect.any(Function));
});

it("passes the existing combined-mode nutrition contract through the same shell", () => {
  const safety: SafetyProfileInput = {
    conditions: [],
    medications: [],
    dangerous_food_reaction_history: false,
    pregnant: false,
    breastfeeding: false,
    eating_disorder_diagnosed: false,
    eating_disorder_active_symptoms: false,
    emergency_or_danger_symptoms: false,
    complex_medication_food_interaction: false,
    physician_dietary_restrictions: null,
    other_relevant_condition: null,
  };
  const structuredExercise = { trains: false } as const;
  sessionStorage.setItem(
    PENDING_NUTRITION_BASICS_KEY,
    JSON.stringify({ safety, structuredExercise }),
  );
  profileContext.productMode = "both";
  const { container } = renderOnboarding();

  expect(screen.getByRole("heading", { name: "Nutrition flow" })).toBeInTheDocument();
  expect(container.querySelector(".public-onboarding__stage"))
    .toContainElement(screen.getByRole("heading", { name: "Nutrition flow" }));
  expect(nutritionFlow.props).toMatchObject({
    productMode: "both",
    trainingProfileExists: false,
    initialDraft: { mode: "both", safety, structuredExercise },
    onCreateTrainingProfile: profileContext.createProfile,
    onComplete: profileContext.retryProfile,
    onNutritionComplete: expect.any(Function),
    editExisting: true,
  });
});
