export const reviewDisclosureKeys = {
  profileBodyTraining: "profile-body-training",
  profileNutrition: "profile-nutrition",
  profileMedical: "profile-medical",
  coachRationale: "coach-rationale",
  coachWorkoutDay: "coach-workout-day",
  coachWorkoutExercise: "coach-workout-exercise",
  physicianEvidence: "physician-evidence",
  physicianNutrients: "physician-nutrients",
  physicianPlanDay: "physician-plan-day",
  physicianPlanMeal: "physician-plan-meal",
} as const;

export type ReviewDisclosureKey =
  (typeof reviewDisclosureKeys)[keyof typeof reviewDisclosureKeys];

export const reviewDisclosureDefaults: Readonly<Record<ReviewDisclosureKey, boolean>> = {
  "profile-body-training": false,
  "profile-nutrition": false,
  "profile-medical": false,
  "coach-rationale": false,
  "coach-workout-day": false,
  "coach-workout-exercise": false,
  "physician-evidence": false,
  "physician-nutrients": false,
  "physician-plan-day": false,
  "physician-plan-meal": false,
};

export function reviewDisclosureDefaultExpanded(key: ReviewDisclosureKey): boolean {
  return reviewDisclosureDefaults[key];
}
