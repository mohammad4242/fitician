import { type ReactNode, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { BrandLogo } from "../../shared/BrandLogo";
import { useAuth } from "../auth/AuthContext";
import { NutritionOnboardingFlow } from "../nutrition/NutritionOnboardingFlow";
import {
  clearPendingNutritionBasics,
  loadPendingNutritionSetup,
} from "../publicOnboarding/onboardingDraft";
import { GuidedSharedProfileQuestions } from "../publicOnboarding/GuidedSharedProfileQuestions";
import { GuidedTrainingQuestions } from "../publicOnboarding/GuidedTrainingQuestions";
import { ModeSelection, type OnboardingLanguage } from "../publicOnboarding/ModeSelection";
import { useProfile } from "./ProfileContext";
import {
  toProfileInput,
  validateStep,
  type ProfileValidationErrors,
} from "./profileValidation";
import type { ProductMode, ProfileFormValue, ProfileFormValues } from "./types";
import "../publicOnboarding/publicOnboarding.css";
import "./profile.css";

const emptyValues: ProfileFormValues = {
  display_name: "",
  birth_date: "",
  sex: "",
  height_cm: "",
  current_weight_kg: "",
  shoulder_circumference_cm: "",
  waist_circumference_cm: "",
  hip_circumference_cm: "",
  fitness_goal: "",
  experience_level: "",
  training_age_months: "",
  training_days_per_week: "",
  preferred_weekdays: [],
  priority_muscle: "",
  training_location: "",
  home_training_setup: "",
  available_equipment: [],
  session_duration_minutes: "",
  training_intensity: "",
  training_cautions: null,
  plan_duration_weeks: "4",
};

export function OnboardingPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const {
    createProfile,
    profile,
    productMode,
    retryProfile,
    selectProductMode,
    status,
  } = useProfile();
  const [values, setValues] = useState<ProfileFormValues>(emptyValues);
  const [errors, setErrors] = useState<ProfileValidationErrors>({});
  const [submitError, setSubmitError] = useState<unknown | null>(null);
  const [busy, setBusy] = useState(false);
  const [trainingStep, setTrainingStep] = useState(false);
  const language: OnboardingLanguage = i18n.resolvedLanguage === "en" ? "en" : "fa";
  const pendingNutritionSetup = loadPendingNutritionSetup();

  function chooseMode(mode: ProductMode) {
    if (busy) return;
    setBusy(true);
    void selectProductMode(mode)
      .catch((cause: unknown) => setSubmitError(cause))
      .finally(() => setBusy(false));
  }

  useEffect(() => {
    const firstInvalidField = Object.keys(errors)[0];
    if (firstInvalidField !== undefined) {
      document
        .querySelector<HTMLElement>("[name=\"" + firstInvalidField + "\"]")
        ?.focus();
    }
  }, [errors]);

  function updateValue(field: keyof ProfileFormValues, value: ProfileFormValue) {
    if (busy) return;
    const changesTrainingLocation = field === "training_location";
    setValues((current) => ({
      ...current,
      [field]: value,
      ...(changesTrainingLocation
        ? { home_training_setup: "", available_equipment: [] }
        : {}),
    }));
    setErrors((current) => {
      if (
        current[field] === undefined
        && (!changesTrainingLocation || current.home_training_setup === undefined)
      ) {
        return current;
      }
      const next = { ...current };
      delete next[field];
      if (changesTrainingLocation) {
        delete next.home_training_setup;
        delete next.available_equipment;
      }
      return next;
    });
  }

  function completeSharedQuestions(
    nextValues: ProfileFormValues = values,
  ): ProfileValidationErrors {
    const nextErrors = {
      ...validateStep(nextValues, 1, new Date()),
      ...validateStep(nextValues, 2, new Date()),
    };
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length === 0) {
      setSubmitError(null);
      setTrainingStep(true);
    }
    return nextErrors;
  }

  function completeTrainingQuestions() {
    if (busy) return;
    const nextErrors = validateStep(values, 3, new Date());
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setBusy(true);
    setSubmitError(null);
    void createProfile(toProfileInput(values))
      .then(() => navigate("/body-progress/new", { replace: true }))
      .catch((cause: unknown) => setSubmitError(cause))
      .finally(() => setBusy(false));
  }

  function returnToSharedQuestions() {
    if (busy) return;
    setErrors({});
    setSubmitError(null);
    setTrainingStep(false);
  }

  if (status === "missing") {
    return (
      <OnboardingShell language={language}>
        <ModeSelection
          language={language}
          disabled={busy}
          onChoose={chooseMode}
        />
        {submitError !== null && (
          <AppErrorNotice
            audience="member"
            context="profile"
            error={submitError}
            locale={language}
          />
        )}
      </OnboardingShell>
    );
  }

  if (productMode === "nutrition" || productMode === "both") {
    return (
      <OnboardingShell language={language}>
        <NutritionOnboardingFlow
          productMode={productMode}
          trainingProfileExists={profile !== null}
          initialDraft={pendingNutritionSetup === null ? undefined : {
            mode: productMode,
            safety: pendingNutritionSetup.safety,
            structuredExercise: pendingNutritionSetup.structuredExercise,
          }}
          initialNutritionBasics={pendingNutritionSetup?.nutritionBasics}
          onCreateTrainingProfile={createProfile}
          onComplete={retryProfile}
          onNutritionComplete={clearPendingNutritionBasics}
          editExisting
        />
      </OnboardingShell>
    );
  }

  return (
    <OnboardingShell language={language}>
      <section className="public-question-card public-question-card--fullscreen">
        {trainingStep ? (
          <GuidedTrainingQuestions
            values={values}
            onChange={updateValue}
            onBack={returnToSharedQuestions}
            onComplete={completeTrainingQuestions}
          />
        ) : (
          <GuidedSharedProfileQuestions
            values={values}
            onChange={updateValue}
            onComplete={completeSharedQuestions}
          />
        )}
        {submitError !== null && (
          <AppErrorNotice
            audience="member"
            context="profile"
            error={submitError}
            locale={language}
          />
        )}
      </section>
    </OnboardingShell>
  );
}

function OnboardingShell({
  children,
  language,
}: {
  children: ReactNode;
  language: OnboardingLanguage;
}) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown | null>(null);

  function handleLogout() {
    setBusy(true);
    setError(null);
    void logout()
      .then(() => {
        // Let the protected route process the cleared user before returning to the public route.
        window.setTimeout(() => navigate("/", { replace: true }), 0);
      })
      .catch((cause: unknown) => setError(cause))
      .finally(() => setBusy(false));
  }

  return (
    <main
      className="public-onboarding authenticated-onboarding"
      dir={language === "fa" ? "rtl" : "ltr"}
    >
      <header className="public-onboarding__header">
        <Link
          className="fitician-brand-link public-onboarding__brand"
          to="/"
          aria-label={t("common.brand")}
        >
          <BrandLogo testId="authenticated-onboarding-brand-logo" />
        </Link>
        <div className="authenticated-onboarding__header-actions">
          <button
            className="logout-button"
            type="button"
            disabled={busy}
            onClick={handleLogout}
          >
            {busy ? t("header.loggingOut") : t("header.logout")}
          </button>
        </div>
      </header>
      {error !== null && (
        <div className="authenticated-onboarding__session-error">
          <AppErrorNotice
            audience="member"
            context="auth"
            error={error}
            locale={language}
            onRetry={handleLogout}
          />
        </div>
      )}
      <div className="public-onboarding__stage">{children}</div>
    </main>
  );
}
