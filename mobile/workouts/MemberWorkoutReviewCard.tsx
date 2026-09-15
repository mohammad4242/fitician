import {
  reviewDisclosureDefaultExpanded,
  reviewDisclosureKeys,
} from "@fitician/core";
import { useState } from "react";
import { StyleSheet, Text, View } from "react-native";

import { Button } from "../ui/components/Button";
import { Card } from "../ui/components/Card";
import { DisclosureCard } from "../ui/components/DisclosureCard";
import { TextField } from "../ui/components/Input";
import { RTL_ROW, RTL_TEXT } from "../ui/rtl";
import { formatPersianNumber } from "../ui/locale";
import { fiticianTokens } from "../ui/tokens";
import type { WorkoutPlan, WorkoutPlanExercise } from "./workoutApi";
import type { MemberWorkoutReview } from "./workoutReviewApi";

export interface MemberWorkoutReviewCardProps {
  readonly busy: boolean;
  readonly onAccept: () => void;
  readonly onReject: (explanation: string) => void;
  readonly review: MemberWorkoutReview;
}

const changeLabels: Record<string, string> = {
  day_added: "افزودن روز",
  day_removed: "حذف روز",
  day_title_changed: "عنوان روز",
  exercise_added: "افزودن حرکت",
  exercise_changed: "تغییر حرکت",
  exercise_reordered: "ترتیب حرکت",
  exercise_removed: "حذف حرکت",
  notes_changed: "یادداشت حرکت",
  prescription_changed: "نوع اجرا",
  reps_range_changed: "محدوده تکرار",
  rest_changed: "زمان استراحت",
  rir_changed: "RIR",
  sets_changed: "تعداد ست",
};

export function MemberWorkoutReviewCard({
  busy,
  onAccept,
  onReject,
  review,
}: MemberWorkoutReviewCardProps) {
  const [explanation, setExplanation] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const canRespond = review.status === "awaiting_member_acceptance";

  function reject() {
    const normalized = explanation.trim();
    if (normalized.length === 0) {
      setValidationError("برای درخواست اصلاح، توضیح خودت را بنویس.");
      return;
    }
    setValidationError(null);
    onReject(normalized);
  }

  return (
    <Card style={styles.card} testID="member-workout-review">
      <View style={styles.heading}>
        <View style={styles.headingCopy}>
          <Text accessibilityRole="header" style={styles.title}>تغییرات پیشنهادی مربی</Text>
          <Text style={styles.status}>
            {canRespond
              ? "در انتظار تایید شما"
              : "درخواست اصلاح ثبت شد؛ پیشنهاد به مربی برگشت."}
          </Text>
        </View>
      </View>

      <Text style={styles.intro}>
        {canRespond
          ? "برنامه فعلی تا زمانی که تأیید نکنی فعال می‌ماند."
          : "پیشنهاد و توضیح تو برای مربی ارسال شده و برنامه فعلی همچنان فعال است."}
      </Text>

      {review.coach_display_name ? (
        <Text style={styles.body}>مربی: <Text style={styles.emphasis}>{review.coach_display_name}</Text></Text>
      ) : null}
      {review.coach_note ? (
        <View style={styles.note}>
          <Text style={styles.noteTitle}>یادداشت مربی</Text>
          <Text style={styles.body}>{review.coach_note}</Text>
        </View>
      ) : null}

      <PlanComparison review={review} />

      <View style={styles.section}>
        <View style={styles.sectionHeading}>
          <Text style={styles.sectionTitle}>خلاصه تغییرات</Text>
          <Text style={styles.muted}>{formatPersianNumber(review.difference_summary.length)} تغییر</Text>
        </View>
        {review.difference_summary.length === 0 ? (
          <Text style={styles.muted}>تغییر ساختاری ثبت نشده است.</Text>
        ) : (
          review.difference_summary.map((difference, index) => (
            <DifferenceRow
              difference={difference}
              key={`${difference.change_type}-${difference.day_number}-${difference.order_index}-${index}`}
              review={review}
            />
          ))
        )}
      </View>

      {review.proposed_plan ? <ProposedPlan plan={review.proposed_plan} /> : null}

      {review.member_rejection_note ? (
        <View style={styles.rejection}>
          <Text style={styles.noteTitle}>توضیح درخواست اصلاح</Text>
          <Text style={styles.body}>{review.member_rejection_note}</Text>
        </View>
      ) : null}

      <View style={styles.response}>
        <TextField
          editable={!busy && canRespond}
          label="دلیل درخواست اصلاح"
          maxLength={2000}
          multiline
          numberOfLines={4}
          onChangeText={(value) => {
            setExplanation(value);
            if (validationError !== null) setValidationError(null);
          }}
          value={explanation}
        />
        {validationError ? <Text accessibilityRole="alert" style={styles.validation}>{validationError}</Text> : null}
        <View style={styles.actions}>
          <Button
            disabled={busy || !canRespond || explanation.trim().length === 0}
            label="درخواست اصلاح"
            loading={busy}
            onPress={reject}
            variant="danger"
          />
          <Button
            disabled={busy || !canRespond}
            label="تأیید تغییرات مربی"
            loading={busy}
            onPress={onAccept}
          />
        </View>
      </View>
    </Card>
  );
}

function PlanComparison({ review }: { readonly review: MemberWorkoutReview }) {
  const current = firstExerciseName(review.source_plan);
  const proposed = review.proposed_plan === null ? null : firstExerciseName(review.proposed_plan);
  const proposedLabel = proposed === current ? "همان حرکت" : proposed ?? "پیشنهاد مربی";

  return (
    <View accessibilityLabel="مقایسه نسخه‌ها" style={styles.comparison}>
      <View style={styles.comparisonItem}>
        <Text style={styles.muted}>نسخه فعلی</Text>
        <Text style={styles.comparisonValue}>{current ?? "برنامه فعلی"}</Text>
      </View>
      <Text accessibilityElementsHidden style={styles.arrow}>→</Text>
      <View style={styles.comparisonItem}>
        <Text style={styles.muted}>نسخه پیشنهادی</Text>
        <Text style={styles.comparisonValue}>{proposedLabel}</Text>
      </View>
    </View>
  );
}

function DifferenceRow({
  difference,
  review,
}: {
  readonly difference: Record<string, unknown>;
  readonly review: MemberWorkoutReview;
}) {
  const changeType = stringValue(difference.change_type) ?? "change";
  const label = changeLabels[changeType] ?? changeType;
  const dayNumber = numberValue(difference.day_number);
  const orderIndex = numberValue(difference.order_index);

  return (
    <View style={styles.difference}>
      <View style={styles.differenceHeading}>
        <Text style={styles.differenceLabel}>{label}</Text>
        <Text style={styles.muted}>
          روز {formatPersianNumber(dayNumber ?? 0)} · حرکت {formatPersianNumber(orderIndex ?? 0)}
        </Text>
      </View>
      <View style={styles.beforeAfter}>
        <View style={styles.valueBlock}>
          <Text style={styles.muted}>قبل</Text>
          <Text style={styles.value}>{formatDifferenceValue(difference.generated, changeType, review.source_plan)}</Text>
        </View>
        <Text accessibilityElementsHidden style={styles.arrow}>→</Text>
        <View style={styles.valueBlock}>
          <Text style={styles.muted}>بعد</Text>
          <Text style={styles.value}>{formatDifferenceValue(difference.approved, changeType, review.proposed_plan)}</Text>
        </View>
      </View>
    </View>
  );
}

function ProposedPlan({ plan }: { readonly plan: WorkoutPlan }) {
  return (
    <DisclosureCard
      defaultExpanded={reviewDisclosureDefaultExpanded(reviewDisclosureKeys.coachRationale)}
      style={styles.proposal}
      summary="روزها و حرکت‌های پیشنهادی"
      title="مشاهده ساختار کامل برنامه پیشنهادی"
    >
      {plan.days.map((day) => (
        <DisclosureCard
          defaultExpanded={reviewDisclosureDefaultExpanded(reviewDisclosureKeys.coachWorkoutDay)}
          key={day.id}
          summary={`${formatPersianNumber(day.exercises.length)} حرکت`}
          title={`روز ${formatPersianNumber(day.day_number)} · ${day.title_fa}`}
        >
          {day.exercises.map((exercise) => (
            <DisclosureCard
              defaultExpanded={reviewDisclosureDefaultExpanded(reviewDisclosureKeys.coachWorkoutExercise)}
              key={exercise.id}
              summary={formatExerciseTarget(exercise)}
              title={`حرکت ${formatPersianNumber(exercise.order_index)} · ${exercise.exercise.name_fa}`}
            >
              <Text style={styles.body}>{exercise.notes_fa ?? "بدون یادداشت"}</Text>
            </DisclosureCard>
          ))}
        </DisclosureCard>
      ))}
    </DisclosureCard>
  );
}

function formatDifferenceValue(value: unknown, changeType: string, plan: WorkoutPlan | null): string {
  if (typeof value === "number") {
    if (changeType === "rest_changed") return `${formatPersianNumber(value)} ثانیه`;
    return formatPersianNumber(value);
  }
  if (typeof value === "string") {
    return findExerciseName(plan, value) ?? value;
  }
  const record = asRecord(value);
  if (record === null) return value === null || value === undefined ? "—" : JSON.stringify(value);
  if (changeType === "reps_range_changed") {
    const minimum = numberValue(record.min);
    const maximum = numberValue(record.max);
    if (minimum !== null && maximum !== null) return `${formatPersianNumber(minimum)}–${formatPersianNumber(maximum)} تکرار`;
  }
  if (changeType === "notes_changed") return stringValue(record.fa) ?? "بدون یادداشت";
  if (changeType === "exercise_added" || changeType === "exercise_removed") {
    const exerciseId = stringValue(record.exercise_id);
    return findExerciseName(plan, exerciseId) ?? exerciseId ?? "حرکت";
  }
  if (changeType === "day_added" || changeType === "day_removed" || changeType === "day_title_changed") {
    return stringValue(record.title_fa) ?? "روز";
  }
  if (changeType === "prescription_changed") {
    return record.mode === "duration" ? "زمانی" : "تکراری";
  }
  return JSON.stringify(record);
}

function formatExerciseTarget(exercise: WorkoutPlanExercise): string {
  if (exercise.prescription_mode === "duration") {
    const minimum = exercise.duration_min_seconds ?? 0;
    const maximum = exercise.duration_max_seconds ?? minimum;
    return `${formatPersianNumber(exercise.sets)} × ${formatPersianNumber(minimum)}–${formatPersianNumber(maximum)} ثانیه`;
  }
  const minimum = exercise.reps_min ?? 0;
  const maximum = exercise.reps_max ?? minimum;
  return `${formatPersianNumber(exercise.sets)} × ${formatPersianNumber(minimum)}–${formatPersianNumber(maximum)} تکرار`;
}

function firstExerciseName(plan: WorkoutPlan): string | null {
  return plan.days[0]?.exercises[0]?.exercise.name_fa ?? null;
}

function findExerciseName(plan: WorkoutPlan | null, exerciseId: string | null): string | null {
  if (plan === null || exerciseId === null) return null;
  for (const day of plan.days) {
    const exercise = day.exercises.find((item) => item.exercise.id === exerciseId);
    if (exercise) return exercise.exercise.name_fa;
  }
  return null;
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? value as Record<string, unknown> : null;
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}

const styles = StyleSheet.create({
  actions: { gap: fiticianTokens.spacing[3] },
  arrow: { color: fiticianTokens.colors.aqua, fontSize: fiticianTokens.typography.fontSize.lg },
  beforeAfter: { ...RTL_ROW, alignItems: "center", gap: fiticianTokens.spacing[3] },
  body: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, lineHeight: 22 },
  card: { gap: fiticianTokens.spacing[4] },
  comparison: { ...RTL_ROW, alignItems: "center", backgroundColor: fiticianTokens.colors.surfaceSubtle, borderColor: fiticianTokens.colors.line, borderRadius: fiticianTokens.radii.medium, borderWidth: 1, gap: fiticianTokens.spacing[3], padding: fiticianTokens.spacing[3] },
  comparisonItem: { flex: 1, gap: fiticianTokens.spacing[1] },
  comparisonValue: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.body, fontWeight: fiticianTokens.typography.fontWeight.bold },
  difference: { backgroundColor: fiticianTokens.colors.surfaceSubtle, borderColor: fiticianTokens.colors.line, borderRadius: fiticianTokens.radii.medium, borderWidth: 1, gap: fiticianTokens.spacing[3], padding: fiticianTokens.spacing[3] },
  differenceHeading: { ...RTL_ROW, alignItems: "center", justifyContent: "space-between", gap: fiticianTokens.spacing[2] },
  differenceLabel: { ...RTL_TEXT, color: fiticianTokens.colors.ink, flex: 1, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, fontWeight: fiticianTokens.typography.fontWeight.bold },
  emphasis: { color: fiticianTokens.colors.ink, fontWeight: fiticianTokens.typography.fontWeight.bold },
  heading: { ...RTL_ROW, alignItems: "flex-start", gap: fiticianTokens.spacing[3] },
  headingCopy: { flex: 1, gap: fiticianTokens.spacing[1] },
  intro: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.body, lineHeight: 24 },
  muted: { ...RTL_TEXT, color: fiticianTokens.colors.muted, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs, lineHeight: 20 },
  note: { backgroundColor: fiticianTokens.colors.infoSurface, borderColor: fiticianTokens.colors.aqua, borderRadius: fiticianTokens.radii.medium, borderWidth: 1, gap: fiticianTokens.spacing[2], padding: fiticianTokens.spacing[3] },
  noteTitle: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm, fontWeight: fiticianTokens.typography.fontWeight.bold },
  proposal: { padding: 0 },
  rejection: { backgroundColor: fiticianTokens.colors.warningSurface, borderColor: fiticianTokens.colors.amber, borderRadius: fiticianTokens.radii.medium, borderWidth: 1, gap: fiticianTokens.spacing[2], padding: fiticianTokens.spacing[3] },
  response: { gap: fiticianTokens.spacing[3] },
  section: { gap: fiticianTokens.spacing[3] },
  sectionHeading: { ...RTL_ROW, alignItems: "center", justifyContent: "space-between", gap: fiticianTokens.spacing[2] },
  sectionTitle: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.lg, fontWeight: fiticianTokens.typography.fontWeight.bold },
  status: { ...RTL_TEXT, color: fiticianTokens.colors.aqua, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.xs },
  title: { ...RTL_TEXT, color: fiticianTokens.colors.ink, fontFamily: fiticianTokens.typography.fontFamily.displayPersian, fontSize: fiticianTokens.typography.fontSize.h2, fontWeight: fiticianTokens.typography.fontWeight.extraBold, lineHeight: 34 },
  validation: { ...RTL_TEXT, color: fiticianTokens.colors.danger, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.sm },
  value: { ...RTL_TEXT, color: fiticianTokens.colors.ink, flex: 1, fontFamily: fiticianTokens.typography.fontFamily.bodyPersian, fontSize: fiticianTokens.typography.fontSize.body, fontWeight: fiticianTokens.typography.fontWeight.bold },
  valueBlock: { flex: 1, gap: fiticianTokens.spacing[1] },
});
