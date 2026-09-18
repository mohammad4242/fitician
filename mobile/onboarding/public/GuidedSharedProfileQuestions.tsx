import { useEffect, useRef, useState } from "react";
import { Pressable, Text, View } from "react-native";

import type { ProfileFormValues } from "@fitician/core/profile";

import { AppIcon, Button, PersianDatePicker, TextField } from "../../ui/components";
import { fiticianTokens } from "../../ui/tokens";
import { PublicChoiceCard, PublicQuestionFrame } from "./PublicQuestionFrame";
import { publicOnboardingStyles as styles } from "./publicOnboardingStyles";
import { usePublicAutoAdvance } from "./usePublicAutoAdvance";

type SharedField = "display_name" | "birth_date" | "sex" | "height_cm" | "current_weight_kg" | "fitness_goal";

export interface GuidedSharedProfileQuestionsProps {
  readonly onBack: () => void;
  readonly onChange: (field: SharedField, value: string) => void;
  readonly onComplete: (values: ProfileFormValues) => void;
  readonly onRegisterBack?: (handler: () => void) => () => void;
  readonly values: ProfileFormValues;
}

const stages = ["شخصی", "بدن", "هدف"] as const;
const titles = [
  "دوست داری چه صدایت کنیم؟",
  "چه تاریخی به دنیا آمدی؟",
  "جنسیتت چیست؟",
  "قد و وزنت چقدر است؟",
  "هدف اصلی تو چیست؟",
] as const;

const sexOptions = [
  { icon: "genderFemale" as const, label: "زن", value: "female" },
  { icon: "genderMale" as const, label: "مرد", value: "male" },
] as const;

const goalOptions = [
  { label: "کاهش وزن 🔻", value: "lose_weight" },
  { label: "افزایش وزن 🔺️", value: "gain_weight" },
  { label: "چربی‌سوزی 🔥", value: "fat_loss" },
  { label: "عضله‌سازی 💪", value: "build_muscle" },
  { label: "چربی‌سوزی + عضله‌سازی 🔥💪", value: "body_recomposition" },
] as const;

function ageOn(birthDate: Date, today: Date): number {
  return today.getUTCFullYear()
    - birthDate.getUTCFullYear()
    - (today.getUTCMonth() < birthDate.getUTCMonth()
      || (today.getUTCMonth() === birthDate.getUTCMonth() && today.getUTCDate() < birthDate.getUTCDate())
      ? 1
      : 0);
}

function validBirthDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/u.test(value)) return false;
  const date = new Date(`${value}T00:00:00.000Z`);
  if (Number.isNaN(date.getTime()) || date.toISOString().slice(0, 10) !== value) return false;
  return ageOn(date, new Date()) >= 18
    && ageOn(date, new Date()) <= 100;
}

function birthDateIsPresent(value: string): boolean {
  return value.trim().length > 0;
}

/* The form/API contract stays Gregorian ISO; only the picker presentation is Jalali. */
function validBirthDateForForm(value: string): boolean {
  return validBirthDate(value);
}

export function GuidedSharedProfileQuestions({
  onBack,
  onChange,
  onComplete,
  onRegisterBack,
  values,
}: GuidedSharedProfileQuestionsProps) {
  const [question, setQuestion] = useState(0);
  const [birthError, setBirthError] = useState<string | null>(null);
  const [showBodyConfirmation, setShowBodyConfirmation] = useState(false);
  const [bodyValuesConfirmed, setBodyValuesConfirmed] = useState(false);
  const { resetAdvancing, selectAndAdvance } = usePublicAutoAdvance();
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const activeStage = question <= 2 ? 0 : question === 3 ? 1 : 2;
  const needsBodyConfirmation = Number(values.height_cm) < 140
    || Number(values.height_cm) > 210
    || Number(values.current_weight_kg) < 40
    || Number(values.current_weight_kg) > 180;
  const ready = [
    values.display_name.trim().length >= 2 && values.display_name.trim().length <= 80,
    birthDateIsPresent(values.birth_date),
    values.sex !== "",
    Number.isFinite(Number(values.height_cm))
      && Number(values.height_cm) >= 120
      && Number(values.height_cm) <= 230
      && Number.isFinite(Number(values.current_weight_kg))
      && Number(values.current_weight_kg) >= 35
      && Number(values.current_weight_kg) <= 300,
    values.fitness_goal !== "",
  ][question];

  function submit() {
    if (question === 1) {
      if (!validBirthDateForForm(values.birth_date)) {
        setBirthError("تاریخ تولد باید معتبر باشد و سن بین ۱۸ تا ۱۰۰ سال باشد.");
        return;
      }
      setBirthError(null);
    }
    if (question === 3 && needsBodyConfirmation && !bodyValuesConfirmed) {
      setShowBodyConfirmation(true);
      return;
    }
    if (question === titles.length - 1) onCompleteRef.current(values);
    else setQuestion((current) => current + 1);
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

  return (
    <PublicQuestionFrame
      activeStage={activeStage}
      footer={question === 0 || question === 1 || question === 3 ? (
        <Button
          disabled={!ready}
          label="ادامه"
          onPress={submit}
        />
      ) : undefined}
      onBack={handleBack}
      onRegisterBack={onRegisterBack}
      progressLabel={`مرحله ${question + 1} از ${titles.length}`}
      question={question}
      stageLabel="بخش‌های پروفایل"
      stages={stages}
      testID="public-shared-questions"
      title={titles[question]}
      totalQuestions={titles.length}
    >
      {question === 0 ? (
        <TextField
          autoFocus
          autoCapitalize="words"
          label="نام نمایشی"
          maxLength={80}
          onChangeText={(value) => onChange("display_name", value)}
          value={values.display_name}
        />
      ) : null}
      {question === 1 ? (
        <View style={styles.fieldStack}>
          <Text style={styles.questionDescription}>روز، ماه و سال تولد را انتخاب کن.</Text>
          <PersianDatePicker
            accessibilityLabel="تاریخ تولد"
            error={birthError ?? undefined}
            label="تاریخ تولد"
            onChange={(value) => {
              setBirthError(null);
              onChange("birth_date", value);
            }}
            testID="public-birth-date"
            value={values.birth_date}
          />
        </View>
      ) : null}
      {question === 2 ? (
        <View style={styles.sexChoiceGrid}>
          {sexOptions.map((option) => (
            <PublicChoiceCard
              {...option}
              key={option.value}
              layout="sex"
              onPress={() => selectAndAdvance(
                () => onChange("sex", option.value),
                () => setQuestion(3),
              )}
              selected={values.sex === option.value}
            />
          ))}
        </View>
      ) : null}
      {question === 3 ? (
        <View style={styles.bodyFields}>
          <TextField
            keyboardType="number-pad"
            hint="۱۲۰ تا ۲۳۰ سانتی‌متر"
            label="قد (سانتی‌متر)"
            maxLength={3}
            onChangeText={(value) => updateBodyValue("height_cm", value)}
            textDirection="ltr"
            value={values.height_cm}
          />
          <TextField
            keyboardType="decimal-pad"
            hint="۳۵ تا ۳۰۰ کیلوگرم"
            label="وزن فعلی (کیلوگرم)"
            maxLength={6}
            onChangeText={(value) => updateBodyValue("current_weight_kg", value)}
            textDirection="ltr"
            value={values.current_weight_kg}
          />
          {showBodyConfirmation ? (
            <Pressable
              accessibilityLabel="این مقادیر درست هستند."
              accessibilityRole="checkbox"
              accessibilityState={{ checked: bodyValuesConfirmed }}
              onPress={() => setBodyValuesConfirmed((current) => !current)}
              style={styles.bodyConfirmation}
            >
              <AppIcon
                color={bodyValuesConfirmed ? fiticianTokens.colors.aqua : fiticianTokens.colors.muted}
                name={bodyValuesConfirmed ? "check" : "close"}
                size={20}
              />
              <Text style={styles.bodyConfirmationText}>این مقادیر درست هستند.</Text>
            </Pressable>
          ) : null}
        </View>
      ) : null}
      {question === 4 ? (
        <View style={styles.choiceGrid}>
          {goalOptions.map((option) => (
            <PublicChoiceCard
              {...option}
              key={option.value}
              onPress={() => selectAndAdvance(
                () => onChange("fitness_goal", option.value),
                () => onCompleteRef.current({ ...values, fitness_goal: option.value }),
              )}
              selected={values.fitness_goal === option.value}
            />
          ))}
        </View>
      ) : null}
    </PublicQuestionFrame>
  );
}
