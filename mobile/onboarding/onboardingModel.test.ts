import { expect, it } from "vitest";

import {
  exerciseInputFromForm,
  nutritionInputFromForms,
  profileValidationMessage,
  safetyInputFromForm,
  type ExerciseFormValues,
  type NutritionBasicsFormValues,
  type NutritionPreferencesFormValues,
  type SafetyFormValues,
} from "./onboardingModel";

it("uses the exact preferred weekday validation message", () => {
  expect(profileValidationMessage("preferredWeekdaysInvalid")).toBe(
    "تعداد روزهای انتخابی باید دقیقاً برابر تعداد روزهای تمرین در هفته باشد.",
  );
});

it("normalizes safety text fields and preserves every safety flag", () => {
  const values: SafetyFormValues = {
    conditions: "دیابت، other",
    medications: "Metformin, Vitamin D",
    dangerous_food_reaction_history: true,
    pregnant: false,
    breastfeeding: false,
    eating_disorder_diagnosed: false,
    eating_disorder_active_symptoms: false,
    emergency_or_danger_symptoms: false,
    complex_medication_food_interaction: true,
    physician_dietary_restrictions: "  no raw grapefruit  ",
    other_relevant_condition: "",
  };

  expect(safetyInputFromForm(values)).toEqual({
    conditions: [
      { code: "other", details: null },
    ],
    medications: [
      { name: "Metformin", dosage: null, notes: null },
      { name: "Vitamin D", dosage: null, notes: null },
    ],
    dangerous_food_reaction_history: true,
    pregnant: false,
    breastfeeding: false,
    eating_disorder_diagnosed: false,
    eating_disorder_active_symptoms: false,
    emergency_or_danger_symptoms: false,
    complex_medication_food_interaction: true,
    physician_dietary_restrictions: "no raw grapefruit",
    other_relevant_condition: null,
  });
});

it("does not submit exercise details when the user does not train", () => {
  const values: ExerciseFormValues = {
    trains: false,
    exercise_type: "mixed",
    days_per_week: "4",
    minutes_per_session: "60",
    intensity: "vigorous",
  };

  expect(exerciseInputFromForm(values)).toEqual({ trains: false });
});

it("maps nutrition basics and preferences into the backend nutrition contract", () => {
  const basics: NutritionBasicsFormValues = {
    daily_activity_level: "moderate",
    monthly_food_budget_toman: "۳۰۰۰۰۰۰",
    budget_style: "strict",
    target_weight_change_kg_per_week: "۰٫۵",
    weight_rate_mode: "safe",
    allergies: [
      { target_type: "food", target_id: "food-peanut", name_fa: "بادام زمینی", name_en: "Peanut", category: "nuts", image_url: null, details: null },
      { target_type: "food", target_id: "food-shrimp", name_fa: "میگو", name_en: "Shrimp", category: "seafood", image_url: null, details: null },
    ],
    intolerances: [
      { target_type: "food", target_id: "food-lactose", name_fa: "شیر", name_en: "Milk", category: "dairy", image_url: null, details: null },
    ],
    dietary_pattern: "omnivore",
  };
  const preferences: NutritionPreferencesFormValues = {
    meals_per_day: "3",
    snacks_per_day: "1",
    preferred_plan_start_day: "saturday",
    favourite_foods: [
      { target_type: "food", target_id: "food-rice", name_fa: "برنج", name_en: "Rice", category: "grain", image_url: null },
      { target_type: "food", target_id: "food-chicken", name_fa: "مرغ", name_en: "Chicken", category: "poultry", image_url: null },
    ],
    disliked_foods: [
      { target_type: "food", target_id: "food-coriander", name_fa: "گشنیز", name_en: "Coriander", category: "herb", image_url: null },
    ],
    religious_cultural_exclusions: "",
    work_shift_context: "",
    daily_check_in_enabled: false,
    preferred_check_in_time: "21:00",
  };

  expect(nutritionInputFromForms(basics, preferences)).toEqual(expect.objectContaining({
    daily_activity_level: "moderate",
    individual_monthly_food_budget_irr: 30_000_000,
    target_weight_change_kg_per_week: 0.5,
    weight_rate_mode: "safe",
    main_meal_count_bucket: "three_main_meals",
    snack_count_bucket: "one_snack",
    meals_per_day: 3,
    snacks_per_day: 1,
    allergy_catalogue_items: [
      { target_type: "food", target_id: "food-peanut", details: null },
      { target_type: "food", target_id: "food-shrimp", details: null },
    ],
    intolerance_catalogue_items: [{ target_type: "food", target_id: "food-lactose", details: null }],
    favourite_catalogue_items: [
      { target_type: "food", target_id: "food-rice" },
      { target_type: "food", target_id: "food-chicken" },
    ],
    disliked_catalogue_items: [{ target_type: "food", target_id: "food-coriander" }],
    allergies: [],
    intolerances: [],
    favourite_foods: [],
    disliked_foods: [],
    preferred_check_in_time: null,
  }));
});
