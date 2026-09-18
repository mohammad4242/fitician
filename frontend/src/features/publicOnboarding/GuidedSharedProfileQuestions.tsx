import { type FormEvent, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { getProfileBirthDateBounds } from "@fitician/core/profile-validation";

import { AppIcon } from "../../shared/AppIcon";
import { PersianDatePicker } from "../../shared/PersianDatePicker";
import type { ProfileValidationErrors } from "../profile/profileValidation";
import type { ProfileFormValues } from "../profile/types";
import { useAutoAdvance } from "./useAutoAdvance";

type Props = {
  values: ProfileFormValues;
  onChange: (field: keyof ProfileFormValues, value: string) => void;
  onBack: () => void;
  onComplete: (values: ProfileFormValues) => ProfileValidationErrors | void;
};

const sexes = ["female", "male"] as const;
const goals = [
  ["lose_weight", "🔻⬆️"],
  ["gain_weight", "🔺️⬇️"],
  ["fat_loss", "🔥"],
  ["build_muscle", "💪"],
  ["body_recomposition", "🔥💪"],
] as const;

function parseIsoDate(value: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value)) return null;
  const date = new Date(`${value}T00:00:00.000Z`);
  return Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value ? null : date;
}

export function GuidedSharedProfileQuestions({ values, onChange, onBack, onComplete }: Props) {
  const { t, i18n } = useTranslation();
  const language = i18n.resolvedLanguage === "en" ? "en" : "fa";
  const [question, setQuestion] = useState(0);
  const [birthError, setBirthError] = useState<string | null>(null);
  const [showBodyConfirmation, setShowBodyConfirmation] = useState(false);
  const [bodyValuesConfirmed, setBodyValuesConfirmed] = useState(false);
  const { selectAndAdvance, resetAdvancing } = useAutoAdvance();
  const onCompleteRef = useRef(onComplete);
  const birthDateBounds = getProfileBirthDateBounds(new Date());
  useEffect(() => {
    onCompleteRef.current = onComplete;
  });

  const labels = language === "en"
    ? ["What should we call you?", "When were you born?", "What is your sex?", "What are your height and weight?", "What is your main goal?"]
    : ["دوست داری چه صدایت کنیم؟", "چه تاریخی به دنیا آمدی؟", "جنسیتت چیست؟", "قد و وزنت چقدر است؟", "هدف اصلی تو چیست؟"];
  const next = language === "en" ? "Continue" : "ادامه";
  const back = language === "en" ? "Back" : "بازگشت";
  const activeStage = question <= 2 ? 0 : question === 3 ? 1 : 2;
  const stages = language === "en" ? ["Personal", "Body", "Goal"] : ["شخصی", "بدن", "هدف"];
  const ready = [
    values.display_name.trim().length >= 2,
    true,
    values.sex !== "",
    Number(values.height_cm) >= 120 && Number(values.height_cm) <= 230
      && Number(values.current_weight_kg) >= 35 && Number(values.current_weight_kg) <= 300,
    values.fitness_goal !== "",
  ][question];
  const needsBodyConfirmation = Number(values.height_cm) < 140 || Number(values.height_cm) > 210
    || Number(values.current_weight_kg) < 40 || Number(values.current_weight_kg) > 180;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (question === 1) {
      const birthError = getBirthDateError(values.birth_date);
      setBirthError(birthError);
      if (birthError !== null) return;
    }
    if (question === 3 && needsBodyConfirmation && !bodyValuesConfirmed) {
      setShowBodyConfirmation(true);
      return;
    }
    if (question === labels.length - 1) {
      const completionErrors = onCompleteRef.current(values);
      if (completionErrors?.birth_date !== undefined) {
        setBirthError(getBirthDateError(values.birth_date) ?? t("onboarding.validation.birthDateInvalid"));
        setQuestion(1);
      }
      return;
    }
    setQuestion((current) => current + 1);
  }

  function getBirthDateError(value: string): string | null {
    const trimmedValue = value.trim();
    if (parseIsoDate(trimmedValue) === null) return t("onboarding.validation.birthDateInvalid");
    if (trimmedValue > birthDateBounds.max) return t("onboarding.validation.birthDateUnder18");
    if (trimmedValue < birthDateBounds.min) return t("onboarding.validation.birthDateOutOfRange");
    return null;
  }

  function handleBack() {
    resetAdvancing();
    if (question === 0) onBack();
    else setQuestion((current) => current - 1);
  }

  function updateBodyValue(field: "height_cm" | "current_weight_kg", value: string) {
    setShowBodyConfirmation(false);
    setBodyValuesConfirmed(false);
    onChange(field, value);
  }

  const showContinue = question === 0 || question === 1 || question === 3;

  return (
    <section className="guided-question" aria-labelledby="guided-question-title">
      <div className="guided-question__nav">
        <button
          type="button"
          className="guided-back-button"
          onClick={handleBack}
          aria-label={back}
        >
          <AppIcon name="arrow" />
        </button>
      </div>
      <ol className="guided-stage-track" aria-label={language === "en" ? "Profile sections" : "بخش‌های پروفایل"}>{stages.map((stage, index) => <li className={index < activeStage ? "is-complete" : index === activeStage ? "is-active" : ""} key={stage}><span aria-hidden="true">{index < activeStage ? "✓" : index + 1}</span>{stage}</li>)}</ol>
      <div className="public-onboarding-progress" aria-label={language === "en" ? "Personal details progress" : "پیشرفت اطلاعات شخصی"}>
        <span>{language === "en" ? `Step ${question + 1} of ${labels.length}` : `مرحله ${question + 1} از ${labels.length}`}</span>
        <progress value={question + 1} max={labels.length} />
      </div>
      <h1 className="fitician-display" id="guided-question-title">{labels[question]}</h1>
      <form className="guided-question__form" onSubmit={submit}>
        {question === 0 && <label>{t("onboarding.fields.displayName")}<input name="display_name" autoFocus required minLength={2} maxLength={80} value={values.display_name} onChange={(event) => onChange("display_name", event.target.value)} /></label>}
        {question === 1 && (
          <div className="birth-date-picker">
            <PersianDatePicker
              ariaLabel={t("onboarding.fields.birthDate")}
              label={t("onboarding.fields.birthDate")}
              max={birthDateBounds.max}
              maxError={t("onboarding.validation.birthDateUnder18")}
              min={birthDateBounds.min}
              minError={t("onboarding.validation.birthDateOutOfRange")}
              onChange={(value) => {
                setBirthError(null);
                onChange("birth_date", value);
              }}
              error={birthError ?? undefined}
              value={values.birth_date}
            />
          </div>
        )}
        {question === 2 && (
          <div className="guided-choice-grid guided-choice-grid--sex">
            {sexes.map((sex) => (
              <button
                className={`guided-choice-card ${values.sex === sex ? "is-selected" : ""}`}
                key={sex}
                type="button"
                onClick={() => selectAndAdvance(
                  () => onChange("sex", sex),
                  () => setQuestion(3),
                )}
              >
                <span className="guided-choice-card__icon" aria-hidden="true">
                  <AppIcon name={sex === "male" ? "male" : "female"} />
                </span>
                <span className="guided-choice-card__label">
                  {t(`onboarding.options.sex.${sex}`)}
                </span>
              </button>
            ))}
          </div>
        )}
        {question === 3 && <div className="guided-body-fields">
          <label>{t("onboarding.fields.height")}<input aria-label={t("onboarding.fields.height")} name="height_cm" type="number" inputMode="numeric" required min={120} max={230} value={values.height_cm} onChange={(event) => updateBodyValue("height_cm", event.target.value)} /><small>{language === "en" ? "120–230 cm" : "۱۲۰ تا ۲۳۰ سانتی‌متر"}</small></label>
          <label>{t("onboarding.fields.weight")}<input aria-label={t("onboarding.fields.weight")} name="current_weight_kg" type="number" inputMode="decimal" required min={35} max={300} step="0.01" value={values.current_weight_kg} onChange={(event) => updateBodyValue("current_weight_kg", event.target.value)} /><small>{language === "en" ? "35–300 kg" : "۳۵ تا ۳۰۰ کیلوگرم"}</small></label>
          {showBodyConfirmation && <label className="guided-body-confirmation"><input type="checkbox" checked={bodyValuesConfirmed} onChange={(event) => setBodyValuesConfirmed(event.target.checked)} />{language === "en" ? "These values are correct." : "این مقادیر درست هستند."}</label>}
        </div>}
        {question === 4 && (
          <div className="guided-choice-grid">
            {goals.map(([goal, emoji]) => (
              <button
                className={values.fitness_goal === goal ? "is-selected" : ""}
                key={goal}
                type="button"
                onClick={() => selectAndAdvance(
                  () => onChange("fitness_goal", goal),
                  () => {
                    const completionErrors = onCompleteRef.current({ ...values, fitness_goal: goal });
                    if (completionErrors?.birth_date !== undefined) {
                      setBirthError(getBirthDateError(values.birth_date) ?? t("onboarding.validation.birthDateInvalid"));
                      setQuestion(1);
                    }
                  },
                )}
              >
                {t(`onboarding.options.fitnessGoal.${goal}`)} {emoji}
              </button>
            ))}
          </div>
        )}

        {showContinue && (
          <div className="profile-actions">
            <button className="primary-button" type="submit" disabled={!ready}>{next}</button>
          </div>
        )}
      </form>
    </section>
  );
}
