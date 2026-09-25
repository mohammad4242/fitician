import { type FormEvent, type ReactNode, useEffect, useId, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { FITICIAN_WEEKDAY_LABELS_FA } from "@fitician/core";
import { AppIcon, type IconName } from "../../shared/AppIcon";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import * as profileApi from "../profile/api";
import {
  toProfileInput,
  validateStep,
  type ProfileValidationErrors,
} from "../profile/profileValidation";
import type { ProductMode, Profile, ProfileFormValue, ProfileFormValues, ProfileInput } from "../profile/types";
import * as nutritionApi from "./api";
import type {
  MedicalConditionCode,
  NutritionCatalogueConstraint,
  NutritionCatalogueConstraintInput,
  NutritionCatalogueTarget,
  NutritionCatalogueTargetInput,
  NutritionProfileInput,
  NutritionProfile,
  SafetyDecision,
  SafetyEvaluation,
  SafetyProfileInput,
} from "./types";
import { CatalogueTargetMultiSelect } from "./CatalogueTargetMultiSelect";
import type { OnboardingDraft, PreAccountNutritionBasics } from "../publicOnboarding/onboardingDraft";
import { GuidedSharedProfileQuestions } from "../publicOnboarding/GuidedSharedProfileQuestions";
import { GuidedTrainingQuestions } from "../publicOnboarding/GuidedTrainingQuestions";
import { useAutoAdvance } from "../publicOnboarding/useAutoAdvance";
import { NutritionExerciseQuestions } from "./NutritionExerciseQuestions";
import { formatTomanInput, irrToToman, tomanToIrr } from "./money";
import type { StructuredExerciseInput } from "./types";
import "./nutritionOnboarding.css";

type FlowStep =
  | "loading"
  | "personal"
  | "body"
  | "safety"
  | "pre_account"
  | "blocked"
  | "training"
  | "budget"
  | "foods"
  | "review"
  | "complete";

type Props = {
  productMode: Extract<ProductMode, "nutrition" | "both">;
  onCreateTrainingProfile: (input: ProfileInput) => Promise<Profile>;
  onComplete: () => void;
  trainingProfileExists?: boolean;
  draftMode?: boolean;
  initialDraft?: OnboardingDraft;
  onDraftChange?: (changes: Partial<OnboardingDraft>) => void;
  onDraftComplete?: (changes: Partial<OnboardingDraft>) => void;
  onExit?: () => void;
  initialNutritionBasics?: PreAccountNutritionBasics;
  onNutritionComplete?: () => void;
  editExisting?: boolean;
  onBack?: () => void;
};

const planStartDayValues = [
  "saturday",
  "sunday",
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
] as const;
const planStartDayLabelsEn = [
  "Saturday",
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
] as const;

const emptyProfileValues: ProfileFormValues = {
  display_name: "", birth_date: "", sex: "", height_cm: "", current_weight_kg: "",
  shoulder_circumference_cm: "", waist_circumference_cm: "", hip_circumference_cm: "",
  fitness_goal: "", experience_level: "", training_days_per_week: "",
  training_location: "", home_training_setup: "", session_duration_minutes: "",
  training_intensity: "",
  training_age_months: "",
  preferred_weekdays: [], priority_muscle: "",
  training_cautions: null, plan_duration_weeks: "4",
};

function draftValues(draft?: OnboardingDraft): ProfileFormValues {
  const source = draft?.training ?? draft?.shared;
  if (source === undefined) return emptyProfileValues;
  return {
    ...emptyProfileValues,
    display_name: source.display_name,
    birth_date: source.birth_date,
    sex: source.sex,
    height_cm: String(source.height_cm),
    current_weight_kg: String(source.current_weight_kg),
    fitness_goal: source.fitness_goal,
    ...(draft?.training === undefined ? {} : {
      shoulder_circumference_cm: draft.training.shoulder_circumference_cm === null ? "" : String(draft.training.shoulder_circumference_cm),
      waist_circumference_cm: draft.training.waist_circumference_cm === null ? "" : String(draft.training.waist_circumference_cm),
      hip_circumference_cm: draft.training.hip_circumference_cm === null ? "" : String(draft.training.hip_circumference_cm),
      experience_level: draft.training.experience_level,
      training_days_per_week: String(draft.training.training_days_per_week),
      training_location: draft.training.training_location,
      home_training_setup: draft.training.home_training_setup ?? "",
      session_duration_minutes: String(draft.training.session_duration_minutes),
      training_intensity: draft.training.training_intensity ?? "",
      priority_muscle: draft.training.priority_muscles?.length === 1
        ? draft.training.priority_muscles[0]
        : "",
      training_cautions: draft.training.training_cautions,
      plan_duration_weeks: String(draft.training.plan_duration_weeks),
    }),
  };
}

const conditionOptions: Array<[MedicalConditionCode, string, string]> = [
  ["controlled_hypertension", "فشار خون کنترل‌شده", "Controlled high blood pressure"],
  ["lipid_disorder", "اختلال چربی خون", "Lipid disorder"],
  ["type_2_diabetes_non_insulin", "دیابت نوع ۲ بدون انسولین", "Type 2 diabetes without insulin"],
  ["stable_gastrointestinal", "مشکل پایدار گوارشی", "Stable gastrointestinal condition"],
  ["kidney_disease", "بیماری کلیه", "Kidney disease"],
  ["dialysis", "دیالیز", "Dialysis"],
  ["liver_disease", "بیماری کبد", "Liver disease"],
  ["insulin_treated_diabetes", "دیابت با درمان انسولین", "Insulin-treated diabetes"],
  ["other", "بیماری یا شرایط دیگر", "Other condition"],
];

const splitNames = (value: string) => value.split(/[،,\n]/).map((item) => item.trim()).filter(Boolean);

function targetFromInput(target: NutritionCatalogueTargetInput): NutritionCatalogueTarget {
  return {
    target_type: target.target_type,
    target_id: target.target_id,
    name_fa: target.target_id,
    name_en: target.target_id,
    category: null,
    image_url: null,
  };
}

function constraintFromInput(target: NutritionCatalogueConstraintInput): NutritionCatalogueConstraint {
  return { ...targetFromInput(target), details: target.details };
}

function targetInput(target: NutritionCatalogueTarget): NutritionCatalogueTargetInput {
  return { target_type: target.target_type, target_id: target.target_id };
}

function constraintInput(target: NutritionCatalogueConstraint): NutritionCatalogueConstraintInput {
  return { ...targetInput(target), details: target.details };
}

const flowCopy = {
  fa: {
    loading: "در حال آماده‌کردن مسیرت…", eyebrow: "مسیر تغذیه با مربی فیتیشن", progress: "پیشرفت تکمیل پروفایل",
  },
  en: {
    loading: "Preparing your path…", eyebrow: "Nutrition with your Fitician coach", progress: "Profile setup progress",
  },
} as const;

export function NutritionOnboardingFlow({
  productMode,
  onCreateTrainingProfile,
  onComplete,
  trainingProfileExists = false,
  draftMode = false,
  initialDraft,
  onDraftChange,
  onDraftComplete,
  onExit,
  initialNutritionBasics,
  onNutritionComplete,
  editExisting = false,
  onBack,
}: Props) {
  const { i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "en" ? "en" : "fa";
  const copy = flowCopy[language];
  const [step, setStep] = useState<FlowStep>(draftMode ? "personal" : "loading");
  const [values, setValues] = useState<ProfileFormValues>(() => draftValues(initialDraft));
  const [, setErrors] = useState<ProfileValidationErrors>({});
  const [busy, setBusy] = useState(false);
  const [requestError, setRequestError] = useState<unknown>(null);
  const [detailsSaved, setDetailsSaved] = useState(false);
  const [decision, setDecision] = useState<SafetyDecision | SafetyEvaluation | null>(null);
  const [conditions, setConditions] = useState<MedicalConditionCode[]>(() => initialDraft?.safety?.conditions.map((item) => item.code) ?? []);
  const [safetyFlags, setSafetyFlags] = useState({
    dangerous_food_reaction_history: initialDraft?.safety?.dangerous_food_reaction_history ?? false,
    pregnant: initialDraft?.safety?.pregnant ?? false,
    breastfeeding: initialDraft?.safety?.breastfeeding ?? false,
    eating_disorder_diagnosed: initialDraft?.safety?.eating_disorder_diagnosed ?? false,
    eating_disorder_active_symptoms: initialDraft?.safety?.eating_disorder_active_symptoms ?? false,
    emergency_or_danger_symptoms: initialDraft?.safety?.emergency_or_danger_symptoms ?? false,
    complex_medication_food_interaction: initialDraft?.safety?.complex_medication_food_interaction ?? false,
  });
  const [medications, setMedications] = useState(() => initialDraft?.safety?.medications.map((item) => item.name).join(", ") ?? "");
  const [physicianRestrictions, setPhysicianRestrictions] = useState(() => initialDraft?.safety?.physician_dietary_restrictions ?? "");
  const [otherCondition, setOtherCondition] = useState(() => initialDraft?.safety?.other_relevant_condition ?? "");
  const [dailyActivityLevel, setDailyActivityLevel] = useState<NutritionProfileInput["daily_activity_level"]>(() => initialNutritionBasics?.daily_activity_level ?? "moderate");
  const [structuredExercise, setStructuredExercise] = useState<StructuredExerciseInput | undefined>(() => initialDraft?.structuredExercise);
  const [budget, setBudget] = useState(() => initialNutritionBasics === undefined ? "" : irrToToman(initialNutritionBasics.individual_monthly_food_budget_irr));
  const [budgetStyle, setBudgetStyle] = useState<"strict" | "flexible">(() => initialNutritionBasics?.budget_style ?? "strict");
  const [targetWeightChangeRate, setTargetWeightChangeRate] = useState<string>(() => {
    if (initialNutritionBasics?.target_weight_change_kg_per_week != null) {
      return String(initialNutritionBasics.target_weight_change_kg_per_week);
    }
    return "";
  });
  const [weightRateMode, setWeightRateMode] = useState<"safe" | "user_override">(
    () => initialNutritionBasics?.weight_rate_mode ?? "safe"
  );
  const [mealCount, setMealCount] = useState("3");
  const [snackCount, setSnackCount] = useState("1");
  const [startDay, setStartDay] = useState<NutritionProfileInput["preferred_plan_start_day"]>("saturday");
  const planStyle = initialNutritionBasics?.plan_style ?? "balanced";
  const [foods, setFoods] = useState<FoodsState>(() => ({
    favourites: (initialNutritionBasics?.favourite_catalogue_items ?? []).map(targetFromInput),
    disliked: (initialNutritionBasics?.disliked_catalogue_items ?? []).map(targetFromInput),
    allergies: (initialNutritionBasics?.allergy_catalogue_items ?? []).map(constraintFromInput),
    intolerances: (initialNutritionBasics?.intolerance_catalogue_items ?? []).map(constraintFromInput),
    cultural: "", workContext: "",
    dietaryPattern: initialNutritionBasics?.dietary_pattern ?? "omnivore",
    checkIn: false, checkInTime: "21:00",
  }));

  const isWeightLoss = values.fitness_goal === "lose_weight" || values.fitness_goal === "fat_loss";
  const isWeightGain = values.fitness_goal === "gain_weight" || values.fitness_goal === "build_muscle";
  const isWeightChangeGoal = isWeightLoss || isWeightGain;

  useEffect(() => {
    if (draftMode) return;
    let active = true;
    void Promise.all([
      profileApi.getSharedProfile(),
      nutritionApi.getSafetyDecision(),
      nutritionApi.getNutritionProfile(),
      nutritionApi.getStructuredExercise(),
    ]).then(([shared, savedDecision, nutrition, savedExercise]) => {
      if (!active) return;
      if (savedExercise !== null) {
        setStructuredExercise(savedExercise.trains ? {
          trains: true,
          exercise_type: savedExercise.exercise_type ?? "other",
          days_per_week: savedExercise.days_per_week ?? 1,
          minutes_per_session: savedExercise.minutes_per_session ?? 30,
          intensity: savedExercise.intensity ?? "moderate",
        } : { trains: false });
      }
      if (shared !== null) {
        setValues((current) => ({
          ...current,
          display_name: shared.display_name,
          birth_date: shared.birth_date,
          sex: shared.sex,
          height_cm: String(shared.height_cm),
          current_weight_kg: String(shared.current_weight_kg),
          fitness_goal: shared.fitness_goal,
        }));
      }
      if (nutrition !== null) {
        setDecision(savedDecision);
        if (!editExisting) {
          setStep("complete");
          return;
        }
        populateExistingNutrition(nutrition);
        setStep("budget");
        return;
      }
      setDecision(savedDecision);
      if (savedDecision !== null && !savedDecision.can_continue_onboarding) {
        setStep("blocked");
      } else if (savedDecision !== null) {
        setStep(productMode === "nutrition" || !trainingProfileExists ? "training" : "budget");
      } else {
        setStep(shared === null ? "personal" : "safety");
      }
    }).catch((cause) => {
      if (active) {
        setRequestError(cause);
        setStep("personal");
      }
    });
    return () => { active = false; };
  }, [draftMode, editExisting, onComplete, productMode, trainingProfileExists]);

  function populateExistingNutrition(nutrition: NutritionProfile) {
    setDailyActivityLevel(nutrition.daily_activity_level);
    setBudget(irrToToman(nutrition.individual_monthly_food_budget_irr));
    setBudgetStyle(nutrition.budget_style);
    if (nutrition.target_weight_change_kg_per_week != null) {
      setTargetWeightChangeRate(String(nutrition.target_weight_change_kg_per_week));
    }
    if (nutrition.weight_rate_mode) {
      setWeightRateMode(nutrition.weight_rate_mode);
    }
    setMealCount(String(nutrition.effective_main_meal_slots ?? nutrition.meals_per_day));
    setSnackCount(String(nutrition.effective_snack_slots ?? nutrition.snacks_per_day));
    setStartDay(nutrition.preferred_plan_start_day);
    setFoods({
      favourites: nutrition.favourite_catalogue_items ?? [],
      disliked: nutrition.disliked_catalogue_items ?? [],
      allergies: nutrition.allergy_catalogue_items ?? [],
      intolerances: nutrition.intolerance_catalogue_items ?? [],
      cultural: nutrition.religious_cultural_exclusions.join(", "),
      workContext: nutrition.work_shift_context ?? "",
      dietaryPattern: nutrition.dietary_pattern,
      checkIn: nutrition.daily_check_in_enabled,
      checkInTime: nutrition.preferred_check_in_time?.slice(0, 5) ?? "21:00",
    });
  }

  function updateProfileValue(
    field: keyof ProfileFormValues,
    value: ProfileFormValue,
  ) {
    setValues((current) => ({
      ...current,
      [field]: value,
      ...(field === "training_location" && value === "gym"
        ? { home_training_setup: "", available_equipment: [] }
        : {}),
    }));
    setErrors((current) => {
      const next = { ...current };
      delete next[field];
      return next;
    });
  }

  function saveShared() {
    const nextErrors = { ...validateStep(values, 1, new Date()), ...validateStep(values, 2, new Date()) };
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    const shared = {
      display_name: values.display_name.trim(),
      birth_date: values.birth_date,
      sex: values.sex as Exclude<typeof values.sex, "">,
      height_cm: Number(values.height_cm),
      current_weight_kg: Number(values.current_weight_kg),
      fitness_goal: values.fitness_goal as Exclude<typeof values.fitness_goal, "">,
    };
    if (draftMode) {
      onDraftChange?.({ shared });
      setStep("training");
      return;
    }
    setBusy(true);
    setRequestError(null);
    void profileApi.saveSharedProfile(shared).then(() => setStep("safety")).catch((cause) => setRequestError(cause)).finally(() => setBusy(false));
  }

  function safetyInput(): SafetyProfileInput {
    return {
      conditions: conditions.map((code) => ({ code, details: null })),
      medications: splitNames(medications).map((name) => ({ name, dosage: null, notes: null })),
      ...safetyFlags,
      physician_dietary_restrictions: physicianRestrictions.trim() || null,
      other_relevant_condition: otherCondition.trim() || null,
    };
  }

  function saveSafety() {
    setBusy(true);
    setRequestError(null);
    const input = safetyInput();
    const request = draftMode
      ? nutritionApi.evaluateSafetyProfile(input)
      : nutritionApi.saveSafetyProfile(input);
    void request.then((result) => {
      if (draftMode) onDraftChange?.({ safety: input });
      setDecision(result);
      if (!result.can_continue_onboarding) setStep("blocked");
      else setStep((productMode === "nutrition" && structuredExercise === undefined) || !trainingProfileExists ? "training" : "budget");
    }).catch((cause) => setRequestError(cause)).finally(() => setBusy(false));
  }

  function saveTraining() {
    const nextErrors = validateStep(values, 3, new Date());
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;
    const training = toProfileInput(values);
    if (draftMode) {
      onDraftChange?.({ training });
      setStep("pre_account");
      return;
    }
    setBusy(true);
    setRequestError(null);
    void onCreateTrainingProfile(training)
      .then(() => setStep("budget"))
      .catch((cause) => setRequestError(cause))
      .finally(() => setBusy(false));
  }

  function saveNutritionExercise(input: StructuredExerciseInput) {
    setStructuredExercise(input);
    if (draftMode) {
      onDraftChange?.({ structuredExercise: input, training: undefined });
      setStep("pre_account");
      return;
    }
    setStep("budget");
  }

  const nutritionInput = useMemo<NutritionProfileInput>(() => {
    const effectiveRate = isWeightChangeGoal
      ? Number(targetWeightChangeRate || (isWeightLoss ? "0.5" : "0.3"))
      : null;
    return {
      daily_activity_level: dailyActivityLevel,
      target_weight_change_kg_per_week: effectiveRate,
      weight_rate_mode: weightRateMode,
      individual_monthly_food_budget_irr: tomanToIrr(budget),
      budget_style: budgetStyle,
      main_meal_count_bucket: mealCount === "2" ? "two_main_meals" : mealCount === "3" ? "three_main_meals" : "four_or_more_main_meals",
      snack_count_bucket: snackCount === "0" ? "zero_snacks" : snackCount === "1" ? "one_snack" : snackCount === "2" ? "two_snacks" : "three_or_more_snacks",
      meals_per_day: Number(mealCount),
      snacks_per_day: Number(snackCount),
      preferred_plan_start_day: startDay,
      favourite_catalogue_items: foods.favourites.map(targetInput),
      disliked_catalogue_items: foods.disliked.map(targetInput),
      allergy_catalogue_items: foods.allergies.map(constraintInput),
      intolerance_catalogue_items: foods.intolerances.map(constraintInput),
      favourite_foods: [],
      disliked_foods: [],
      allergies: [],
      intolerances: [],
      dietary_pattern: foods.dietaryPattern,
      religious_cultural_exclusions: splitNames(foods.cultural),
      work_shift_context: foods.workContext.trim() || null,
      daily_check_in_enabled: foods.checkIn,
      preferred_check_in_time: foods.checkIn ? `${foods.checkInTime}:00` : null,
    };
  }, [budget, budgetStyle, dailyActivityLevel, foods, isWeightChangeGoal, isWeightLoss, mealCount, snackCount, startDay, targetWeightChangeRate, weightRateMode]);

  function finish(event: FormEvent) {
    event.preventDefault();
    if (draftMode) {
      onDraftComplete?.({
        shared: {
          display_name: values.display_name.trim(), birth_date: values.birth_date,
          sex: values.sex as Exclude<typeof values.sex, "">, height_cm: Number(values.height_cm),
          current_weight_kg: Number(values.current_weight_kg),
          fitness_goal: values.fitness_goal as Exclude<typeof values.fitness_goal, "">,
        },
        safety: safetyInput(),
        ...(productMode === "both" ? { training: toProfileInput(values) } : {}),
        nutrition: nutritionInput,
      });
      return;
    }
    setBusy(true);
    setRequestError(null);
    void nutritionApi.saveNutritionProfile(nutritionInput)
      .then(() => {
        if (productMode === "nutrition") {
          if (structuredExercise === undefined) throw new Error("Structured exercise is required");
          return nutritionApi.saveStructuredExercise(structuredExercise);
        }
        return undefined;
      })
      .then(() => nutritionApi.createNutritionEstimate())
      .then(() => {
        onNutritionComplete?.();
        if (productMode === "both") onComplete();
        else setStep("complete");
      })
      .catch((cause) => setRequestError(cause))
      .finally(() => setBusy(false));
  }

  const flowOrder: FlowStep[] = [
    "personal",
    "safety",
    ...(productMode === "nutrition" || !trainingProfileExists ? (["training"] as FlowStep[]) : []),
    "budget",
    "review",
  ];
  const progressIndex = Math.max(flowOrder.indexOf(step), 0) + 1;
  const guidedStep = step !== "review";

  if (step === "loading") return <p aria-live="polite">{copy.loading}</p>;
  if (step === "blocked") {
    return (
      <section className="nutrition-step safety-result-card" aria-live="polite">
        <p className="eyebrow eyebrow--accent">{language === "en" ? "Safety assessment result" : "نتیجه ارزیابی ایمنی"}</p>
        <h2 className="fitician-display">{language === "en" ? "Continue with a Fitician physician" : "ادامه مسیر با پزشک فیتیشن"}</h2>
        <p>{language === "en" ? "For your safety, this path needs review by a Fitician physician." : decision?.message}</p>
        <p>{language === "en" ? "Allowed information is saved and no automatic plan will be created." : "اطلاعات مجاز ذخیره شد و هیچ برنامه خودکاری ساخته نمی‌شود."}</p>
        {draftMode && <button className="primary-button" type="button" onClick={() => onDraftComplete?.({ safety: safetyInput() })}>{language === "en" ? "Continue to account setup" : "ادامه و ساخت حساب"}</button>}
        <button className="secondary-button" type="button" onClick={() => setStep("safety")}>{language === "en" ? "Back and edit answers" : "بازگشت و اصلاح پاسخ‌ها"}</button>
      </section>
    );
  }
  if (step === "complete") {
    return (
      <section className="nutrition-step safety-result-card" aria-live="polite">
        <p className="eyebrow eyebrow--accent">{language === "en" ? "Nutrition profile" : "پروفایل تغذیه"}</p>
        <h2 className="fitician-display">{language === "en" ? "Your nutrition profile is saved" : "پروفایل تغذیه‌ات ثبت شد"}</h2>
        <p>{language === "en" ? "Your safety, budget, and preference information is saved." : "اطلاعات ایمنی، بودجه و ترجیحاتت ذخیره شد."}</p>
        {decision?.requires_physician_review && <p>{language === "en" ? "A Fitician physician will review your nutrition path." : decision.message}</p>}
        <p>{language === "en" ? "No meal plan has been generated yet." : "هنوز هیچ برنامه غذایی تولید نشده است."}</p>
      </section>
    );
  }

  if (editExisting && step === "budget") {
    return (
      <PostAccountNutritionDetails
        language={language}
        busy={busy}
        dailyActivityLevel={dailyActivityLevel}
        budget={budget}
        budgetStyle={budgetStyle}
        mealCount={mealCount}
        snackCount={snackCount}
        startDay={startDay}
        targetWeightChangeRate={targetWeightChangeRate}
        weightRateMode={weightRateMode}
        fitnessGoal={values.fitness_goal}
        foods={foods}
        saved={detailsSaved}
        saveError={requestError}
        onDailyActivityLevel={setDailyActivityLevel}
        onBudget={setBudget}
        onBudgetStyle={setBudgetStyle}
        onMealCount={setMealCount}
        onSnackCount={setSnackCount}
        onStartDay={setStartDay}
        onTargetWeightChangeRate={setTargetWeightChangeRate}
        onWeightRateMode={setWeightRateMode}
        onFoods={setFoods}
        onBack={onBack}
        onSave={() => {
          setBusy(true);
          setRequestError(null);
          setDetailsSaved(false);
          void nutritionApi.saveNutritionProfile(nutritionInput)
            .then(() => {
              if (productMode === "nutrition" && structuredExercise !== undefined) {
                return nutritionApi.saveStructuredExercise(structuredExercise);
              }
              return undefined;
            })
            .then(() => nutritionApi.createNutritionEstimate())
            .then(() => setDetailsSaved(true))
            .catch((cause) => setRequestError(cause))
            .finally(() => setBusy(false));
        }}
      />
    );
  }

  return (
    <section className="nutrition-step" dir={language === "fa" ? "rtl" : "ltr"}>
      {!guidedStep && <><p className="eyebrow eyebrow--accent">{copy.eyebrow}</p>
      <div className="nutrition-progress" aria-label={copy.progress}>
        <span>{language === "en" ? `Step ${progressIndex} of ${flowOrder.length}` : `مرحله ${progressIndex} از ${flowOrder.length}`}</span>
        <progress value={progressIndex} max={flowOrder.length} />
      </div>
      <h2 className="fitician-display">{stepTitle(step, language)}</h2>
      <p>{stepIntro(step, language)}</p></>}
      {decision?.requires_physician_review && step !== "safety" && (
        <p className="nutrition-feedback" role="status">{language === "en" ? "A Fitician physician review is required for your nutrition path." : decision.message}</p>
      )}
      {step === "personal" && (
        <GuidedSharedProfileQuestions values={values} onChange={(field, value) => updateProfileValue(field, value)} onBack={onExit} onComplete={saveShared} />
      )}
      {step === "safety" && (
        <SafetyForm
          language={language}
          busy={busy}
          conditions={conditions}
          flags={safetyFlags}
          medications={medications}
          physicianRestrictions={physicianRestrictions}
          otherCondition={otherCondition}
          foods={foods}
          onFoods={setFoods}
          onConditions={setConditions}
          onFlags={setSafetyFlags}
          onMedications={setMedications}
          onPhysicianRestrictions={setPhysicianRestrictions}
          onOtherCondition={setOtherCondition}
          onComplete={saveSafety}
          onBack={() => setStep("personal")}
          startAfterMedical={!draftMode && initialDraft?.safety !== undefined}
        />
      )}
      {step === "pre_account" && <PreAccountNutritionQuestions
          busy={busy} conditions={conditions} foods={foods} budget={budget} dailyActivityLevel={dailyActivityLevel}
        onConditions={setConditions} onFoods={setFoods} onBudget={(value) => setBudget(formatTomanInput(value))}
        onDailyActivityLevel={setDailyActivityLevel}
        onBack={() => setStep("training")}
        onComplete={() => onDraftComplete?.({ safety: safetyInput(), structuredExercise, nutritionBasics: {
          daily_activity_level: dailyActivityLevel, individual_monthly_food_budget_irr: tomanToIrr(budget), budget_style: budgetStyle, plan_style: planStyle,
          favourite_catalogue_items: foods.favourites.map(targetInput),
          disliked_catalogue_items: foods.disliked.map(targetInput),
          allergy_catalogue_items: foods.allergies.map(constraintInput),
          intolerance_catalogue_items: foods.intolerances.map(constraintInput),
          allergies: [],
          intolerances: [],
          dietary_pattern: foods.dietaryPattern,
        } })}
      />}
      {step === "training" && (
        productMode === "nutrition" ? (
          <NutritionExerciseQuestions
            initialValue={structuredExercise}
            fitnessGoal={values.fitness_goal}
            onBack={() => setStep(draftMode ? "personal" : "safety")}
            onComplete={saveNutritionExercise}
          />
        ) : (
          <GuidedTrainingQuestions
            values={values}
            onChange={updateProfileValue}
            onBack={() => setStep(draftMode ? "personal" : "safety")}
            onComplete={saveTraining}
          />
        )
      )}
      {step === "budget" && (
        <BudgetForm
          busy={busy} budget={budget} budgetStyle={budgetStyle} mealCount={mealCount}
          snackCount={snackCount} startDay={startDay}
          targetWeightChangeRate={targetWeightChangeRate}
          weightRateMode={weightRateMode}
          fitnessGoal={values.fitness_goal}
          onBudget={(value) => setBudget(formatTomanInput(value))}
          onBudgetStyle={setBudgetStyle} onMealCount={setMealCount} onSnackCount={setSnackCount}
          onStartDay={setStartDay}
          onTargetWeightChangeRate={setTargetWeightChangeRate}
          onWeightRateMode={setWeightRateMode}
          onBack={() => setStep(productMode === "nutrition" || !trainingProfileExists ? "training" : "safety")}
          onNext={() => setStep("review")}
        />
      )}
      {step === "review" && (
        <form className="profile-form" onSubmit={finish}>
          <div className="nutrition-review-card">
            <strong>{language === "en" ? `Monthly budget: ${budget} Toman` : `بودجه ماهانه: ${new Intl.NumberFormat("fa-IR").format(Number(budget.replaceAll(",", "")))} تومان`}</strong>
            {isWeightChangeGoal && (
              <span>
                {language === "en"
                  ? `Weekly weight rate: ${targetWeightChangeRate || (isWeightLoss ? "0.5" : "0.3")} kg/week`
                  : `نرخ تغییر وزن هفتگی: ${targetWeightChangeRate || (isWeightLoss ? "0.5" : "0.3")} کیلوگرم در هفته`}
              </span>
            )}
            <span>{language === "en" ? `${mealCount} meals and ${snackCount} snacks per day` : `${mealCount} وعده اصلی و ${snackCount} میان‌وعده در روز`}</span>
            <span>{language === "en" ? "Safety policy" : "سیاست ایمنی"}: {decision?.policy_version}</span>
            <span>{language === "en" ? `Allergies: ${foods.allergies.map((item) => item.name_en).join(", ") || "None"}` : `حساسیت ثبت‌شده: ${foods.allergies.map((item) => item.name_fa).join("، ") || "ندارد"}`}</span>
          </div>
          <Actions busy={busy} onBack={() => setStep("budget")} nextLabel={language === "en" ? "Save nutrition profile" : "ثبت پروفایل تغذیه"} />
        </form>
      )}
      <AppErrorNotice
        audience="member"
        context="nutrition"
        error={requestError}
        locale={language}
      />
    </section>
  );
}

type WeightRateOption = { value: string; label: string; isHigh: boolean };
type NutritionLocalizer = (fa: string, en: string) => string;

function formatPersianRate(value: string) {
  return new Intl.NumberFormat("fa-IR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  }).format(Number(value));
}

function createWeightRateOptions(l: NutritionLocalizer): WeightRateOption[] {
  const options: WeightRateOption[] = [];
  for (let r = 3; r <= 20; r += 1) {
    const value = (r / 10).toFixed(1);
    options.push({
      value,
      label: l(`${formatPersianRate(value)} کیلوگرم در هفته`, `${value} kg/week`),
      isHigh: r > 10,
    });
  }
  return options;
}

function WeightRateSettingBox(props: {
  isLoss: boolean;
  rate: string;
  mode: "safe" | "user_override";
  rateOptions: WeightRateOption[];
  onRate: (value: string) => void;
  onMode: (mode: "safe" | "user_override") => void;
  l: NutritionLocalizer;
}) {
  const { isLoss, rate, mode, rateOptions, onRate, onMode, l } = props;
  const defaultRate = isLoss ? "0.5" : "0.3";
  const selectedRate = rate || defaultRate;
  const currentRateNum = Number(selectedRate);
  const isHigh = currentRateNum > 1.0;
  const selectedOption = rateOptions.find((option) => option.value === selectedRate) ?? {
    value: selectedRate,
    label: l(`${formatPersianRate(selectedRate)} کیلوگرم در هفته`, `${selectedRate} kg/week`),
    isHigh,
  };
  const [isRateListOpen, setIsRateListOpen] = useState(false);
  const settingBoxRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const listboxId = useId();

  useEffect(() => {
    if (!isRateListOpen) return undefined;

    const closeWhenClickedOutside = (event: PointerEvent) => {
      if (!settingBoxRef.current?.contains(event.target as Node)) setIsRateListOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setIsRateListOpen(false);
      triggerRef.current?.focus();
    };

    document.addEventListener("pointerdown", closeWhenClickedOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeWhenClickedOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [isRateListOpen]);

  const focusOption = (index: number) => {
    const nextIndex = (index + rateOptions.length) % rateOptions.length;
    optionRefs.current[nextIndex]?.focus();
  };

  return (
    <div ref={settingBoxRef} className="nutrition-rate-setting-box">
      <div className="nutrition-rate-setting-box__header">
        <h3 className="nutrition-rate-setting-box__title">
          <span className="profile-field__icon-badge" aria-hidden="true">
            <AppIcon name="target" />
          </span>
          <span>
            {isLoss
              ? l("نرخ کاهش وزن هفتگی", "Weekly weight loss rate")
              : l("نرخ افزایش وزن هفتگی", "Weekly weight gain rate")}
          </span>
        </h3>
      </div>

      <div
        className="nutrition-rate-setting-box__modes"
        role="radiogroup"
        aria-label={l("حالت نرخ تغییر وزن", "Weight-rate mode")}
      >
        <button
          type="button"
          role="radio"
          aria-checked={mode === "safe"}
          className={`nutrition-rate-mode-option ${mode === "safe" ? "is-selected" : ""}`}
          onClick={() => onMode("safe")}
        >
          <div className="nutrition-rate-mode-option__head">
            <span className="nutrition-rate-mode-option__radio" aria-hidden="true" />
            <strong>{l("تنظیم ایمن پیشنهادی", "Safe recommended")}</strong>
          </div>
          <p>{l("فیتیشن نرخ انتخابی را در محدوده ایمن تنظیم می‌کند تا از کسری یا مازاد کالری بیش‌ازحد جلوگیری شود.", "Fitician keeps the selected rate within a safe range to avoid an excessive calorie deficit or surplus.")}</p>
          <small className="nutrition-rate-mode-option__helper">{l("اگر نرخ انتخابی بیش از محدوده ایمن باشد، فیتیشن آن را به مقدار ایمن تنظیم می‌کند.", "If the selected rate exceeds the safe range, Fitician adjusts it to a safe value.")}</small>
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={mode === "user_override"}
          className={`nutrition-rate-mode-option ${mode === "user_override" ? "is-selected is-override" : ""}`}
          onClick={() => onMode("user_override")}
        >
          <div className="nutrition-rate-mode-option__head">
            <span className="nutrition-rate-mode-option__radio" aria-hidden="true" />
            <strong>{l("اعمال نرخ دلخواه من", "Custom override")}</strong>
          </div>
          <p>{l("نرخ انتخابی تو مستقیماً اعمال می‌شود؛ حتی اگر بالاتر از نرخ پیشنهادی فیتیشن باشد.", "Your selected rate is applied directly, even if it is above Fitician's recommendation.")}</p>
          <small className="nutrition-rate-mode-option__helper">{l("نرخ انتخابی مستقیماً اعمال می‌شود و ممکن است از نرخ پیشنهادی فیتیشن بیشتر باشد.", "The selected rate is applied directly and may exceed Fitician's recommendation.")}</small>
        </button>
      </div>

      <div className="nutrition-rate-setting-box__rate">
        <span className="nutrition-rate-setting-box__rate-label">{l("نرخ هفتگی", "Weekly rate")}</span>
        <button
          ref={triggerRef}
          type="button"
          className="nutrition-rate-setting-box__trigger"
          aria-haspopup="listbox"
          aria-expanded={isRateListOpen}
          aria-controls={listboxId}
          onClick={() => setIsRateListOpen((current) => !current)}
        >
          <span>{selectedOption.label}</span>
          <AppIcon className="nutrition-rate-setting-box__chevron" name="chevron" />
        </button>
        {isRateListOpen && (
          <div
            id={listboxId}
            className="nutrition-rate-setting-box__options"
            role="listbox"
            aria-label={l("نرخ تغییر وزن هفتگی", "Weekly weight change rate")}
          >
            {rateOptions.map((option, index) => (
              <button
                ref={(element) => { optionRefs.current[index] = element; }}
                key={option.value}
                type="button"
                role="option"
                aria-selected={option.value === selectedRate}
                className={`nutrition-rate-setting-box__option ${option.value === selectedRate ? "is-selected" : ""}`}
                onClick={() => {
                  onRate(option.value);
                  setIsRateListOpen(false);
                  triggerRef.current?.focus();
                }}
                onKeyDown={(event) => {
                  if (event.key === "ArrowDown") {
                    event.preventDefault();
                    focusOption(index + 1);
                  } else if (event.key === "ArrowUp") {
                    event.preventDefault();
                    focusOption(index - 1);
                  } else if (event.key === "Home") {
                    event.preventDefault();
                    focusOption(0);
                  } else if (event.key === "End") {
                    event.preventDefault();
                    focusOption(rateOptions.length - 1);
                  }
                }}
              >
                <span className="nutrition-rate-setting-box__option-label">{option.label}</span>
                {option.isHigh && <span className="nutrition-rate-setting-box__badge">{l("بالا", "High")}</span>}
                {option.value === selectedRate && <span className="nutrition-rate-setting-box__check" aria-hidden="true">✓</span>}
              </button>
            ))}
          </div>
        )}
      </div>

      {isHigh && mode === "user_override" && (
        <div className="nutrition-rate-override-notice" role="status">
          <span aria-hidden="true">⚠</span>
          <span>
            <strong>{l("نرخ بالای ۱ کیلوگرم در هفته انتخاب شده است.", "A rate above 1 kg/week is selected.")}</strong>
            <small>{l("این نرخ به انتخاب مستقیم تو اعمال می‌شود.", "This rate is applied directly by your choice.")}</small>
          </span>
        </div>
      )}
      {isHigh && mode === "safe" && (
        <small className="nutrition-rate-safe-notice">
          {l("نرخ بالای ۱.۰ کیلوگرم در هفته پیشنهاد نمی‌شود.", "Rates above 1.0 kg/week are not recommended.")}
        </small>
      )}
    </div>
  );
}

function PostAccountNutritionDetails(props: {
  language: "fa" | "en";
  busy: boolean;
  dailyActivityLevel: NutritionProfileInput["daily_activity_level"];
  budget: string;
  budgetStyle: NutritionProfileInput["budget_style"];
  mealCount: string;
  snackCount: string;
  startDay: NutritionProfileInput["preferred_plan_start_day"];
  targetWeightChangeRate: string;
  weightRateMode: "safe" | "user_override";
  fitnessGoal: string;
  foods: FoodsState;
  saved: boolean;
  saveError: unknown;
  onDailyActivityLevel: (value: NutritionProfileInput["daily_activity_level"]) => void;
  onBudget: (value: string) => void;
  onBudgetStyle: (value: NutritionProfileInput["budget_style"]) => void;
  onMealCount: (value: string) => void;
  onSnackCount: (value: string) => void;
  onStartDay: (value: NutritionProfileInput["preferred_plan_start_day"]) => void;
  onTargetWeightChangeRate: (value: string) => void;
  onWeightRateMode: (value: "safe" | "user_override") => void;
  onFoods: (value: FoodsState) => void;
  onBack?: () => void;
  onSave: () => void;
}) {
  const l = (fa: string, en: string) => props.language === "en" ? en : fa;
  const isLoss = props.fitnessGoal === "lose_weight" || props.fitnessGoal === "fat_loss";
  const isGain = props.fitnessGoal === "gain_weight" || props.fitnessGoal === "build_muscle";
  const isRecomp = props.fitnessGoal === "body_recomposition";
  const isWeightChangeGoal = isLoss || isGain;

  const rateOptions = createWeightRateOptions(l);

  return (
    <section className="nutrition-step profile-details-page" dir={props.language === "fa" ? "rtl" : "ltr"}>
      <p className="eyebrow eyebrow--accent">{l("پروفایل", "Profile")}</p>
      <h2 className="fitician-display">{l("اطلاعات تغذیه‌ای", "Nutrition information")}</h2>
      <form className="profile-form nutrition-details-form" onSubmit={(event) => { event.preventDefault(); props.onSave(); }}>
        <fieldset className="profile-fieldset" disabled={props.busy}>
          <legend>
            <span className="profile-field__icon-badge" aria-hidden="true">
              <AppIcon name="flame" />
            </span>
            <span>{l("نیاز روزانه و وعده‌ها", "Daily needs and meals")}</span>
          </legend>
          <SelectField icon="flame" label={l("میزان فعالیت روزانه", "Daily activity level")} value={props.dailyActivityLevel} onChange={(value) => props.onDailyActivityLevel(value as NutritionProfileInput["daily_activity_level"])} options={[["sedentary", l("کم‌تحرک", "Sedentary")], ["light", l("فعالیت سبک", "Light")], ["moderate", l("فعالیت متوسط", "Moderate")], ["very_active", l("بسیار فعال", "Very active")]]} />
          <LabeledInput icon="wallet" label={l("بودجه ماهانه غذا (تومان)", "Monthly food budget (Toman)")} inputMode="numeric" required value={props.budget} onChange={props.onBudget} />
          <SelectField icon="target" label={l("نوع بودجه", "Budget style")} value={props.budgetStyle} onChange={(value) => props.onBudgetStyle(value as NutritionProfileInput["budget_style"])} options={[["strict", l("سخت‌گیرانه", "Strict")], ["flexible", l("انعطاف‌پذیر", "Flexible")]]} />
          {isWeightChangeGoal && (
            <WeightRateSettingBox
              isLoss={isLoss}
              rate={props.targetWeightChangeRate}
              mode={props.weightRateMode}
              rateOptions={rateOptions}
              onRate={props.onTargetWeightChangeRate}
              onMode={props.onWeightRateMode}
              l={l}
            />
          )}
          {isRecomp && (
            <p style={{ color: "var(--fitician-aqua)", fontSize: "0.85rem", margin: "0.25rem 0" }}>
              {l("هدف روند وزن: تقریباً ثابت (بدون تغییر وزن هفتگی)", "Target weight trend: approximately stable")}
            </p>
          )}
          <SelectField icon="utensils" label={l("وعده اصلی در روز", "Main meals per day")} value={props.mealCount} onChange={props.onMealCount} options={[["2", l("۲ وعده", "2 meals")], ["3", l("۳ وعده", "3 meals")], ["4", l("۴ وعده یا بیشتر", "4 or more meals")]]} />
          <SelectField icon="nutrition" label={l("میان‌وعده در روز", "Snacks per day")} value={props.snackCount} onChange={props.onSnackCount} options={[["0", l("هیچ‌کدام", "None")], ["1", l("۱ میان‌وعده", "1 snack")], ["2", l("۲ میان‌وعده", "2 snacks")], ["3", l("۳ میان‌وعده یا بیشتر", "3 or more snacks")]]} />
          <SelectField icon="catalogue" label={l("الگوی غذایی", "Dietary pattern")} value={props.foods.dietaryPattern} onChange={(value) => props.onFoods({ ...props.foods, dietaryPattern: value as FoodsState["dietaryPattern"] })} options={[["omnivore", l("همه‌چیزخوار", "Omnivore")], ["vegetarian", l("گیاه‌خوار (به‌زودی)", "Vegetarian (Coming soon)"), true], ["vegan", l("وگان (به‌زودی)", "Vegan (Coming soon)"), true]]} />
        </fieldset>
        <fieldset className="profile-fieldset" disabled={props.busy}>
          <legend>
            <span className="profile-field__icon-badge" aria-hidden="true">
              <AppIcon name="heart" />
            </span>
            <span>{l("ترجیحات غذایی", "Food preferences")}</span>
          </legend>
          <CatalogueTargetMultiSelect
            label={l("غذاهایی که دوست داری (اختیاری)", "Foods you like (optional)")}
            value={props.foods.favourites}
            onChange={(favourites) => props.onFoods({ ...props.foods, favourites })}
            language={props.language}
            disabled={props.busy}
          />
          <CatalogueTargetMultiSelect
            label={l("غذاهایی که دوست نداری (اختیاری)", "Foods you dislike (optional)")}
            value={props.foods.disliked}
            onChange={(disliked) => props.onFoods({ ...props.foods, disliked })}
            language={props.language}
            disabled={props.busy}
          />
          <CatalogueTargetMultiSelect
            label={l("حساسیت‌های غذایی (اختیاری)", "Food allergies (optional)")}
            value={props.foods.allergies}
            onChange={(allergies) => props.onFoods({ ...props.foods, allergies })}
            language={props.language}
            includeDetails
            disabled={props.busy}
          />
          <CatalogueTargetMultiSelect
            label={l("عدم‌تحمل‌های غذایی (اختیاری)", "Food intolerances (optional)")}
            value={props.foods.intolerances}
            onChange={(intolerances) => props.onFoods({ ...props.foods, intolerances })}
            language={props.language}
            includeDetails
            disabled={props.busy}
          />
          <TextArea icon="document" label={l("محدودیت مذهبی یا فرهنگی (اختیاری)", "Religious or cultural exclusions (optional)")} value={props.foods.cultural} onChange={(cultural) => props.onFoods({ ...props.foods, cultural })} />
        </fieldset>
        <AppErrorNotice
          audience="member"
          context="nutrition"
          error={props.saveError}
          locale={props.language}
          onRetry={props.onSave}
        />
        {props.saved && <p className="profile-save-message profile-save-message--success" role="status">{l("اطلاعات تغذیه‌ای ذخیره شد.", "Nutrition information was saved.")}</p>}
        <div className="profile-actions profile-wizard__actions">
          {props.onBack && <button className="secondary-button" type="button" disabled={props.busy} onClick={props.onBack}>{l("بازگشت", "Back")}</button>}
          <button className="primary-button" type="submit" disabled={props.busy}>{props.busy ? l("در حال ذخیره…", "Saving…") : l("ذخیره اطلاعات", "Save information")}</button>
        </div>
      </form>
    </section>
  );
}

function stepTitle(step: FlowStep, language: "fa" | "en") {
  const fa = {
    loading: "", personal: "اول کمی با هم آشنا شویم", body: "هدفت را دقیق کنیم",
    safety: "اول ایمنی، بعد برنامه", blocked: "", training: "حالا بخش تمرین را هماهنگ کنیم", pre_account: "چند سؤال کوتاه تغذیه",
    budget: "بودجه و وعده‌ها", foods: "", review: "یک مرور کوتاه قبل از ثبت", complete: "",
  };
  const en = {
    loading: "", personal: "Let’s get to know each other", body: "Let’s define your goal",
    safety: "Safety first, then your plan", blocked: "", training: "Let’s align your training", pre_account: "A few quick nutrition questions",
    budget: "Budget and meals", foods: "", review: "A quick review before saving", complete: "",
  };
  return (language === "en" ? en : fa)[step];
}

function stepIntro(step: FlowStep, language: "fa" | "en") {
  const fa = {
    loading: "", personal: "سؤال‌ها کوتاه‌اند و قدم‌به‌قدم پیش می‌رویم.",
    body: "این اطلاعات بین تمرین و تغذیه مشترک است و فقط یک‌بار ثبت می‌شود.",
    safety: "این پاسخ‌ها برای تشخیص پزشکی نیست؛ فقط مسیر ایمن برنامه را مشخص می‌کند.",
    blocked: "", training: "اطلاعات فعلی تمرینت را صفحه‌به‌صفحه نگه می‌داریم.", pre_account: "بعد از ساخت حساب، فقط جزئیات باقی‌ماندهٔ پروفایل را کامل می‌کنیم.",
    budget: "بودجه شخصی خودت را فقط به تومان وارد کن.", foods: "",
    review: "بعد از ثبت، هنوز هیچ برنامه غذایی تولید نمی‌شود.", complete: "",
  };
  const en = {
    loading: "", personal: "The questions are short; we’ll take them one step at a time.",
    body: "Training and nutrition share this information, so we only ask once.",
    safety: "These answers do not provide a diagnosis; they only help keep your plan safe.",
    blocked: "", training: "We’ll keep your current training details one screen at a time.", pre_account: "After account setup, you will only complete the remaining profile details.",
    budget: "Enter your personal food budget in Toman.", foods: "",
    review: "Saving this does not generate a meal plan yet.", complete: "",
  };
  return (language === "en" ? en : fa)[step];
}

type Flags = SafetyProfileInput extends infer _ ? {
  dangerous_food_reaction_history: boolean; pregnant: boolean; breastfeeding: boolean;
  eating_disorder_diagnosed: boolean; eating_disorder_active_symptoms: boolean;
  emergency_or_danger_symptoms: boolean; complex_medication_food_interaction: boolean;
} : never;

function useLocalizer() {
  const { i18n } = useTranslation();
  return (fa: string, en: string) => i18n.resolvedLanguage === "en" ? en : fa;
}

function NutritionQuestionFrame(props: {
  busy: boolean;
  current: number;
  total: number;
  title: string;
  stage: 0 | 1 | 2;
  optional?: boolean;
  nextLabel?: string;
  showContinue?: boolean;
  hideBottomBack?: boolean;
  onBack: () => void;
  onSubmit: () => void;
  children: ReactNode;
}) {
  const l = useLocalizer();
  const stages = [l("ایمنی", "Safety"), l("سبک زندگی", "Routine"), l("غذاها", "Food")];
  return (
    <section className="guided-question nutrition-question" aria-labelledby="nutrition-question-title">
      <div className="guided-question__nav">
        <button
          type="button"
          className="guided-back-button"
          onClick={props.onBack}
          aria-label={l("بازگشت", "Back")}
        >
          <AppIcon name="arrow" />
        </button>
      </div>
      <ol className="guided-stage-track" aria-label={l("بخش‌های تغذیه", "Nutrition sections")}>
        {stages.map((stage, index) => (
          <li className={index < props.stage ? "is-complete" : index === props.stage ? "is-active" : ""} key={stage}>
            <span aria-hidden="true">{index < props.stage ? "✓" : index + 1}</span>{stage}
          </li>
        ))}
      </ol>
      <div className="public-onboarding-progress" aria-label={l("پیشرفت سؤال‌های تغذیه", "Nutrition questions progress")}>
        <span>{l(`سؤال ${props.current + 1} از ${props.total}`, `Question ${props.current + 1} of ${props.total}`)}</span>
        <progress value={props.current + 1} max={props.total} />
      </div>
      <h1 className="fitician-display" id="nutrition-question-title">{props.title}</h1>
      <form className="guided-question__form" onSubmit={(event) => { event.preventDefault(); props.onSubmit(); }}>
        <fieldset className="nutrition-question__control" disabled={props.busy}>{props.children}</fieldset>
        {props.optional && <button className="text-button" type="submit">{l("رد کردن این سؤال", "Skip this question")}</button>}
        <Actions
          busy={props.busy}
          onBack={props.hideBottomBack ? undefined : props.onBack}
          nextLabel={props.nextLabel ?? l("ادامه", "Continue")}
          showContinue={props.showContinue ?? true}
        />
      </form>
    </section>
  );
}

function SafetyForm(props: {
  language: "fa" | "en";
  busy: boolean; conditions: MedicalConditionCode[]; flags: Flags; medications: string;
  physicianRestrictions: string; otherCondition: string; foods: FoodsState;
  onConditions: (value: MedicalConditionCode[]) => void; onFlags: (value: Flags) => void;
  onMedications: (value: string) => void; onPhysicianRestrictions: (value: string) => void;
  onOtherCondition: (value: string) => void; onFoods: (value: FoodsState) => void; onComplete: () => void; onBack: () => void;
  startAfterMedical?: boolean;
}) {
  const l = useLocalizer();
  const firstQuestion = props.startAfterMedical ? 1 : 0;
  const [question, setQuestion] = useState(firstQuestion);
  const titles = [
    l("آیا شرایط پزشکی مشخصی داری؟", "Do you have any medical conditions?"),
    l("کدام موارد ایمنی دربارهٔ تو صدق می‌کند؟", "Do any of these safety considerations apply?"),
    l("در حال حاضر چه داروهایی مصرف می‌کنی؟", "Which medications do you currently take?"),
    l("پزشک محدودیت غذایی خاصی برایت تعیین کرده؟", "Has a physician prescribed dietary restrictions?"),
    l("شرایط دیگری هست که مربی باید بداند؟", "Is there anything else your coach should know?"),
    l("حساسیت یا عدم‌تحمل غذایی داری؟", "Do you have food allergies or intolerances?"),
  ];
  const advance = () => question === titles.length - 1 ? props.onComplete() : setQuestion((current) => current + 1);
  const back = () => question === firstQuestion ? props.onBack() : setQuestion((current) => current - 1);
  return (
    <NutritionQuestionFrame busy={props.busy} current={question} total={titles.length} title={titles[question]} stage={0}
      optional={question >= 2} nextLabel={question === titles.length - 1 ? l("ثبت ارزیابی ایمنی", "Save safety assessment") : undefined}
      onBack={back} onSubmit={advance}>
        {question === 0 && <div className="profile-checkboxes nutrition-option-grid">
          {conditionOptions.map(([code, fa, en]) => (
            <label className="nutrition-option" key={code}><input type="checkbox" checked={props.conditions.includes(code)}
              onChange={() => props.onConditions(props.conditions.includes(code)
                ? props.conditions.filter((item) => item !== code) : [...props.conditions, code])} />{l(fa, en)}</label>
          ))}
        </div>}
        {question === 1 && <div className="profile-checkboxes nutrition-option-grid">{([
          ["dangerous_food_reaction_history", "سابقه واکنش خطرناک غذایی", "History of dangerous food reaction"],
          ["pregnant", "بارداری", "Pregnant"], ["breastfeeding", "شیردهی", "Breastfeeding"],
          ["eating_disorder_diagnosed", "تشخیص اختلال خوردن", "Diagnosed eating disorder"],
          ["eating_disorder_active_symptoms", "علائم فعال اختلال خوردن", "Active eating-disorder symptoms"],
          ["complex_medication_food_interaction", "تداخل پیچیده دارو و غذا", "Complex medication-food interaction"],
          ["emergency_or_danger_symptoms", "علائم خطر یا وضعیت اورژانسی", "Emergency or danger symptoms"],
        ] as const).map(([field, fa, en]) => (
          <label className="nutrition-check nutrition-option" key={field}><input type="checkbox" checked={props.flags[field]}
            onChange={(event) => props.onFlags({ ...props.flags, [field]: event.target.checked })} />{l(fa, en)}</label>
        ))}</div>}
        {question === 2 && <TextArea label={l("داروهای فعلی (اختیاری، هر دارو یک خط)", "Current medications (optional, one per line)")} value={props.medications} onChange={props.onMedications} />}
        {question === 3 && <TextArea label={l("محدودیت غذایی تجویزشده توسط پزشک (اختیاری)", "Physician-prescribed dietary restrictions (optional)")} value={props.physicianRestrictions} onChange={props.onPhysicianRestrictions} />}
        {question === 4 && <TextArea label={l("شرایط مرتبط دیگر (اختیاری)", "Other relevant conditions (optional)")} value={props.otherCondition} onChange={props.onOtherCondition} />}
        {question === 5 && <div className="nutrition-allergy-fields">
          <CatalogueTargetMultiSelect
            label={l("حساسیت‌های غذایی (اختیاری)", "Food allergies (optional)")}
            value={props.foods.allergies}
            onChange={(allergies) => props.onFoods({ ...props.foods, allergies })}
            language={props.language}
            includeDetails
            disabled={props.busy}
          />
          <CatalogueTargetMultiSelect
            label={l("عدم‌تحمل‌های غذایی (اختیاری)", "Food intolerances (optional)")}
            value={props.foods.intolerances}
            onChange={(intolerances) => props.onFoods({ ...props.foods, intolerances })}
            language={props.language}
            includeDetails
            disabled={props.busy}
          />
        </div>}
    </NutritionQuestionFrame>
  );
}

function PreAccountNutritionQuestions(props: {
  busy: boolean; conditions: MedicalConditionCode[]; foods: FoodsState; budget: string;
  dailyActivityLevel: NutritionProfileInput["daily_activity_level"];
  onConditions: (value: MedicalConditionCode[]) => void;
  onFoods: (value: FoodsState) => void; onBudget: (value: string) => void;
  onDailyActivityLevel: (value: NutritionProfileInput["daily_activity_level"]) => void; onBack: () => void; onComplete: () => void;
}) {
  const l = useLocalizer();
  const [question, setQuestion] = useState(0);
  const titles = [
    l("آیا شرایط پزشکی مشخصی داری؟", "Do you have any medical conditions?"),
    l("میزان فعالیت روزانه‌ات چقدر است؟", "How active are you on a typical day?"),
    l("بودجه ماهانه غذای تو چقدر است؟", "What is your monthly food budget?"),
    l("چه سبک غذایی را ترجیح می‌دهی؟", "Which food style do you prefer?"),
  ];
  const { selectAndAdvance, resetAdvancing } = useAutoAdvance();
  const onCompleteRef = useRef(props.onComplete);
  useEffect(() => {
    onCompleteRef.current = props.onComplete;
  });

  const advance = () => {
    if (question === titles.length - 1) onCompleteRef.current();
    else setQuestion((current) => current + 1);
  };


  const back = () => {
    resetAdvancing();
    if (question === 0) props.onBack();
    else setQuestion((current) => current - 1);
  };

  const showContinue = question === 0 || question === 2 || question === 3;

  return (
    <NutritionQuestionFrame
      busy={props.busy}
      current={question}
      total={titles.length}
      title={titles[question]}
      stage={question === 0 ? 0 : question < 3 ? 1 : 2}
      nextLabel={question === titles.length - 1 ? l("ادامه و ساخت حساب", "Continue to account setup") : undefined}
      showContinue={showContinue}
      hideBottomBack={true}
      onBack={back}
      onSubmit={advance}
    >
      {question === 0 && (
        <div className="profile-checkboxes nutrition-option-grid">
          {conditionOptions.map(([code, fa, en]) => (
            <label className="nutrition-option" key={code}>
              <input
                type="checkbox"
                checked={props.conditions.includes(code)}
                onChange={() => props.onConditions(
                  props.conditions.includes(code)
                    ? props.conditions.filter((item) => item !== code)
                    : [...props.conditions, code],
                )}
              />
              {l(fa, en)}
            </label>
          ))}
        </div>
      )}
      {question === 1 && (
        <div className="guided-choice-grid guided-choice-grid--activity">
          {([
            ["sedentary", l("کم‌تحرک", "Mostly sedentary"), l("بیشتر روز نشسته، بدون تمرین خاص", "Mostly sitting, little to no exercise"), "clock"],
            ["light", l("کمی فعال", "Lightly active"), l("پیاده‌روی روزانه یا کارهای سبک", "Light walking or daily chores"), "scale"],
            ["moderate", l("فعالیت متوسط", "Moderately active"), l("ورزش منظم یا شغل با تحرک ۳ تا ۵ روز در هفته", "Moderate exercise or active job 3-5 days/week"), "flame"],
            ["very_active", l("بسیار فعال", "Very active"), l("تمرین سنگین روزانه یا فعالیت بدنی شدید", "Intense daily training or heavy physical labor"), "zap"],
          ] as const).map(([value, label, desc, icon]) => (
            <button
              key={value}
              type="button"
              className={`guided-choice-card ${props.dailyActivityLevel === value ? "is-selected" : ""}`}
              onClick={() => {
                selectAndAdvance(
                  () => props.onDailyActivityLevel(value as NutritionProfileInput["daily_activity_level"]),
                  () => advance(),
                );
              }}
            >
              <span className="guided-choice-card__icon" aria-hidden="true">
                <AppIcon name={icon as IconName} />
              </span>
              <span className="guided-choice-card__content">
                <strong className="guided-choice-card__label">{label}</strong>
                <small className="guided-choice-card__hint">{desc}</small>
              </span>
            </button>
          ))}
        </div>
      )}
      {question === 2 && (
        <LabeledInput
          label={l("بودجه ماهانه غذا (تومان)", "Monthly food budget (Toman)")}
          inputMode="numeric"
          required
          value={props.budget}
          onChange={props.onBudget}
        />
      )}
      {question === 3 && (
        <div className="guided-choice-grid guided-choice-grid--dietary">
          {([
            ["omnivore", l("همه‌چیزخوار", "Omnivore"), l("انواع مواد غذایی شامل گوشت، مرغ، ماهی، لبنیات و گیاهی", "All food types including meat, poultry, fish, dairy, and plants"), "utensils", false],
            ["vegetarian", l("گیاه‌خوار (به‌زودی)", "Vegetarian (Coming soon)"), l("بدون گوشت، شامل لبنیات و تخم‌مرغ", "No meat, includes dairy and eggs"), "sparkles", true],
            ["vegan", l("وگان (به‌زودی)", "Vegan (Coming soon)"), l("کاملاً گیاهی، بدون فرآورده‌های حیوانی", "Completely plant-based, no animal products"), "sparkles", true],
          ] as const).map(([value, label, desc, icon, disabled]) => (
            <button
              key={value}
              type="button"
              disabled={disabled}
              className={`guided-choice-card ${props.foods.dietaryPattern === value ? "is-selected" : ""} ${disabled ? "is-disabled" : ""}`}
              onClick={() => {
                if (disabled) return;
                selectAndAdvance(
                  () => props.onFoods({
                    ...props.foods,
                    dietaryPattern: value as FoodsState["dietaryPattern"],
                  }),
                  () => advance(),
                );
              }}
            >
              <span className="guided-choice-card__icon" aria-hidden="true">
                <AppIcon name={icon as IconName} />
              </span>
              <span className="guided-choice-card__content">
                <strong className="guided-choice-card__label">{label}</strong>
                <small className="guided-choice-card__hint">{desc}</small>
              </span>
            </button>
          ))}
        </div>
      )}
    </NutritionQuestionFrame>
  );
}


function BudgetForm(props: {
  busy: boolean;
  budget: string;
  budgetStyle: "strict" | "flexible";
  mealCount: string;
  snackCount: string;
  startDay: NutritionProfileInput["preferred_plan_start_day"];
  targetWeightChangeRate: string;
  weightRateMode: "safe" | "user_override";
  fitnessGoal: string;
  onBudget: (value: string) => void;
  onBudgetStyle: (value: "strict" | "flexible") => void;
  onMealCount: (value: string) => void;
  onSnackCount: (value: string) => void;
  onStartDay: (value: NutritionProfileInput["preferred_plan_start_day"]) => void;
  onTargetWeightChangeRate: (value: string) => void;
  onWeightRateMode: (value: "safe" | "user_override") => void;
  onBack: () => void;
  onNext: () => void;
}) {
  const l = useLocalizer();
  const [question, setQuestion] = useState(0);

  const isLoss = props.fitnessGoal === "lose_weight" || props.fitnessGoal === "fat_loss";
  const isGain = props.fitnessGoal === "gain_weight" || props.fitnessGoal === "build_muscle";
  const isWeightChangeGoal = isLoss || isGain;

  const rateOptions = createWeightRateOptions(l);

  const questionsList: Array<{
    id: "budget" | "budget_style" | "weight_rate" | "meals" | "snacks" | "start_day";
    title: string;
  }> = [
    { id: "budget", title: l("بودجه ماهانه غذای تو چقدر است؟", "What is your monthly food budget?") },
    { id: "budget_style", title: l("بودجه را چقدر سخت‌گیرانه رعایت کنیم؟", "How strictly should we follow your budget?") },
  ];

  if (isWeightChangeGoal) {
    questionsList.push({
      id: "weight_rate",
      title: isLoss
        ? l("هفته‌ای چقدر می‌خواهی وزن کم کنی؟", "How much weight do you want to lose per week?")
        : l("هفته‌ای چقدر می‌خواهی وزن اضافه کنی؟", "How much weight do you want to gain per week?"),
    });
  }

  questionsList.push(
    { id: "meals", title: l("روزانه چند وعده اصلی می‌خوری؟", "How many main meals do you eat each day?") },
    { id: "snacks", title: l("روزانه چند میان‌وعده می‌خواهی؟", "How many snacks would you like each day?") },
    { id: "start_day", title: l("برنامه غذایی از چه روزی شروع شود؟", "Which day should your plan start?") },
  );

  const currentQ = questionsList[question];
  const advance = () => (question === questionsList.length - 1 ? props.onNext() : setQuestion((current) => current + 1));
  const back = () => (question === 0 ? props.onBack() : setQuestion((current) => current - 1));

  return (
    <NutritionQuestionFrame
      busy={props.busy}
      current={question}
      total={questionsList.length}
      title={currentQ.title}
      stage={1}
      onBack={back}
      onSubmit={advance}
    >
      {currentQ.id === "budget" && (
        <LabeledInput
          label={l("بودجه ماهانه غذا (تومان)", "Monthly food budget (Toman)")}
          inputMode="numeric"
          required
          value={props.budget}
          onChange={props.onBudget}
        />
      )}
      {currentQ.id === "budget_style" && (
        <SelectField
          label={l("نوع بودجه", "Budget style")}
          value={props.budgetStyle}
          onChange={(value) => props.onBudgetStyle(value as "strict" | "flexible")}
          options={[
            ["strict", l("سخت‌گیرانه", "Strict")],
            ["flexible", l("انعطاف‌پذیر", "Flexible")],
          ]}
        />
      )}
      {currentQ.id === "weight_rate" && (
        <WeightRateSettingBox
          isLoss={isLoss}
          rate={props.targetWeightChangeRate}
          mode={props.weightRateMode}
          rateOptions={rateOptions}
          onRate={props.onTargetWeightChangeRate}
          onMode={props.onWeightRateMode}
          l={l}
        />
      )}
      {currentQ.id === "meals" && (
        <SelectField
          label={l("وعده اصلی در روز", "Main meals per day")}
          value={props.mealCount}
          onChange={props.onMealCount}
          options={[
            ["2", l("۲ وعده", "2 meals")],
            ["3", l("۳ وعده", "3 meals")],
            ["4", l("۴ وعده یا بیشتر", "4 or more meals")],
          ]}
        />
      )}
      {currentQ.id === "snacks" && (
        <SelectField
          label={l("میان‌وعده در روز", "Snacks per day")}
          value={props.snackCount}
          onChange={props.onSnackCount}
          options={[
            ["0", l("هیچ‌کدام", "None")],
            ["1", l("۱ میان‌وعده", "1 snack")],
            ["2", l("۲ میان‌وعده", "2 snacks")],
            ["3", l("۳ میان‌وعده یا بیشتر", "3 or more snacks")],
          ]}
        />
      )}
      {currentQ.id === "start_day" && (
        <SelectField
          label={l("روز شروع برنامه", "Plan start day")}
          value={props.startDay}
          onChange={(value) => props.onStartDay(value as NutritionProfileInput["preferred_plan_start_day"])}
          options={planStartDayValues.map((value, index) => [
            value,
            l(FITICIAN_WEEKDAY_LABELS_FA[index] ?? value, planStartDayLabelsEn[index] ?? value),
          ])}
        />
      )}
    </NutritionQuestionFrame>
  );
}

type FoodsState = {
  favourites: NutritionCatalogueTarget[]; disliked: NutritionCatalogueTarget[];
  allergies: NutritionCatalogueConstraint[]; intolerances: NutritionCatalogueConstraint[];
  cultural: string; workContext: string;
  dietaryPattern: NutritionProfileInput["dietary_pattern"];
  checkIn: boolean; checkInTime: string;
};

function LabeledInput(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  min?: string;
  max?: string;
  required?: boolean;
  inputMode?: "numeric" | "decimal" | "text";
  icon?: IconName;
}) {
  return (
    <div className="profile-field">
      <label className="profile-field-wrapped-label">
        <span className="profile-field__title">
          {props.icon && (
            <span className="profile-field__icon-badge" aria-hidden="true">
              <AppIcon name={props.icon} />
            </span>
          )}
          <span>{props.label}</span>
        </span>
        <input
          type={props.type ?? "text"}
          inputMode={props.inputMode}
          min={props.min}
          max={props.max}
          required={props.required}
          value={props.value}
          onChange={(event) => props.onChange(event.target.value)}
        />
      </label>
    </div>
  );
}

function TextArea(props: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  icon?: IconName;
}) {
  return (
    <div className="profile-field nutrition-question__field">
      <label className="profile-field-wrapped-label">
        <span className="profile-field__title">
          {props.icon && (
            <span className="profile-field__icon-badge" aria-hidden="true">
              <AppIcon name={props.icon} />
            </span>
          )}
          <span>{props.label}</span>
        </span>
        <textarea
          className="nutrition-question__textarea"
          dir="auto"
          value={props.value}
          onChange={(event) => props.onChange(event.target.value)}
        />
      </label>
    </div>
  );
}

function SelectField(props: {
  label: string;
  value: string;
  options: Array<[string, string] | [string, string, boolean]>;
  onChange: (value: string) => void;
  icon?: IconName;
}) {
  return (
    <div className="profile-field">
      <label className="profile-field-wrapped-label">
        <span className="profile-field__title">
          {props.icon && (
            <span className="profile-field__icon-badge" aria-hidden="true">
              <AppIcon name={props.icon} />
            </span>
          )}
          <span>{props.label}</span>
        </span>
        <select
          value={props.value}
          onChange={(event) => props.onChange(event.target.value)}
        >
          {props.options.map(([value, label, disabled]) => (
            <option key={value} value={value} disabled={disabled}>
              {label}
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}

function Actions({
  busy,
  onBack,
  nextLabel,
  showContinue = true,
}: {
  busy: boolean;
  onBack?: () => void;
  nextLabel: string;
  showContinue?: boolean;
}) {
  const l = useLocalizer();
  if (!onBack && !showContinue) return null;
  return (
    <div className="profile-actions">
      {onBack && <button className="secondary-button" type="button" disabled={busy} onClick={onBack}>{l("بازگشت", "Back")}</button>}
      {showContinue && <button className="primary-button" type="submit" disabled={busy}>{busy ? l("در حال ذخیره…", "Saving…") : nextLabel}</button>}
    </div>
  );
}
