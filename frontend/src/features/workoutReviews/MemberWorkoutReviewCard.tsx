import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { WorkoutPlan, WorkoutPlanExercise } from "../workouts/types";
import type { WorkoutReviewDifferenceEntry, WorkoutReviewMemberDetail } from "./types";
import "./memberWorkoutReview.css";

type MemberWorkoutReviewCardProps = {
  review: WorkoutReviewMemberDetail;
  busy: boolean;
  onAccept: () => void;
  onReject: (explanation: string) => void;
};

const changeLabels: Record<string, [string, string]> = {
  day_added: ["افزودن روز", "Day added"],
  day_removed: ["حذف روز", "Day removed"],
  day_title_changed: ["عنوان روز", "Day title"],
  exercise_added: ["افزودن حرکت", "Exercise added"],
  exercise_removed: ["حذف حرکت", "Exercise removed"],
  exercise_reordered: ["ترتیب حرکت", "Exercise order"],
  exercise_changed: ["تغییر حرکت", "Exercise changed"],
  sets_changed: ["تعداد ست", "Sets"],
  prescription_changed: ["نوع اجرا", "Prescription"],
  reps_range_changed: ["محدوده تکرار", "Rep range"],
  rir_changed: ["RIR", "RIR"],
  rest_changed: ["زمان استراحت", "Rest"],
  notes_changed: ["یادداشت حرکت", "Exercise notes"],
};

export function MemberWorkoutReviewCard({
  review,
  busy,
  onAccept,
  onReject,
}: MemberWorkoutReviewCardProps) {
  const { i18n } = useTranslation();
  const isEnglish = i18n.resolvedLanguage === "en";
  const [explanation, setExplanation] = useState("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const canRespond = review.status === "awaiting_member_acceptance";
  const l = (fa: string, en: string) => isEnglish ? en : fa;

  function reject() {
    const normalized = explanation.trim();
    if (!normalized) {
      setValidationError(l("برای درخواست اصلاح، توضیح خودت را بنویس.", "Explain what should be corrected."));
      return;
    }
    setValidationError(null);
    onReject(normalized);
  }

  return (
    <section className="member-workout-review" aria-labelledby="member-workout-review-title">
      <div className="member-workout-review__heading">
        <div>
          <p className="eyebrow eyebrow--accent">{l("بازبینی تغییرات", "Change review")}</p>
          <h2 id="member-workout-review-title">{l("تغییرات پیشنهادی مربی", "Coach-proposed changes")}</h2>
        </div>
        <span className={`member-workout-review__status member-workout-review__status--${review.status}`}>
          {canRespond
            ? l("در انتظار تایید شما", "Waiting for your approval")
            : l("درخواست اصلاح ثبت شد؛ پیشنهاد به مربی برگشت.", "Changes requested; the proposal was returned to the coach.")}
        </span>
      </div>

      <p className="member-workout-review__intro">
        {canRespond
          ? l("برنامه فعلی تا زمانی که تأیید نکنی فعال می‌ماند.", "Your current plan stays active until you approve these changes.")
          : l("پیشنهاد و توضیح تو برای مربی ارسال شده و برنامه فعلی همچنان فعال است.", "Your feedback is with the coach and your current plan remains active.")}
      </p>

      {review.coach_display_name && (
        <p className="member-workout-review__coach">
          {l("مربی:", "Coach:")} <strong>{review.coach_display_name}</strong>
        </p>
      )}

      {review.coach_note && (
        <aside className="member-workout-review__note">
          <strong>{l("یادداشت مربی", "Coach note")}</strong>
          <p>{review.coach_note}</p>
        </aside>
      )}

      <PlanComparison review={review} isEnglish={isEnglish} />

      <section className="member-workout-review__differences" aria-labelledby="member-workout-differences-title">
        <div className="member-workout-review__section-heading">
          <h3 id="member-workout-differences-title">{l("خلاصه تغییرات", "Change summary")}</h3>
          <span>{formatCount(review.difference_summary.length, isEnglish)} {l("تغییر", "changes")}</span>
        </div>
        {review.difference_summary.length === 0 ? (
          <p className="member-workout-review__empty">{l("تغییر ساختاری ثبت نشده است.", "No structural changes were recorded.")}</p>
        ) : (
          <ol>
            {review.difference_summary.map((difference, index) => (
              <DifferenceRow
                key={`${difference.change_type}-${difference.day_number}-${difference.order_index}-${index}`}
                difference={difference}
                review={review}
                isEnglish={isEnglish}
              />
            ))}
          </ol>
        )}
      </section>

      {review.proposed_plan && (
        <details className="member-workout-review__proposal">
          <summary>{l("مشاهده ساختار کامل برنامه پیشنهادی", "View the full proposed plan")}</summary>
          <div className="member-workout-review__proposal-body">
            {review.proposed_plan.days.map((day) => (
              <section key={day.id ?? day.day_number}>
                <h4>{isEnglish ? day.title_en : day.title_fa}</h4>
                <ul>
                  {day.exercises.map((exercise) => (
                    <li key={exercise.id}>
                      <span>{formatCount(exercise.order_index, isEnglish)}.</span>
                      <strong>{isEnglish ? exercise.exercise.name_en : exercise.exercise.name_fa}</strong>
                      <small>{formatExerciseTarget(exercise, isEnglish)}</small>
                    </li>
                  ))}
                </ul>
              </section>
            ))}
          </div>
        </details>
      )}

      {review.member_rejection_note && (
        <aside className="member-workout-review__rejection" role="status">
          <strong>{l("توضیح درخواست اصلاح", "Your correction request")}</strong>
          <p>{review.member_rejection_note}</p>
        </aside>
      )}

      <div className="member-workout-review__response">
        <label htmlFor="member-workout-review-explanation">
          {l("دلیل درخواست اصلاح", "Correction request explanation")}
          <textarea
            id="member-workout-review-explanation"
            value={explanation}
            disabled={busy || !canRespond}
            onChange={(event) => {
              setExplanation(event.target.value);
              if (validationError !== null) setValidationError(null);
            }}
            placeholder={l("مثلاً: حرکت روز اول برای زانویم مناسب نیست.", "For example: the first-day exercise is not suitable for my knee.")}
            maxLength={2000}
          />
        </label>
        {validationError && <p className="member-workout-review__validation" role="alert">{validationError}</p>}
        <div className="member-workout-review__actions">
          <button
            className="member-workout-review__reject"
            type="button"
            disabled={busy || !canRespond || !explanation.trim()}
            onClick={reject}
          >
            {l("درخواست اصلاح", "Request corrections")}
          </button>
          <button
            className="member-workout-review__accept"
            type="button"
            disabled={busy || !canRespond}
            onClick={onAccept}
          >
            {l("تأیید تغییرات مربی", "Approve coach changes")}
          </button>
        </div>
      </div>
    </section>
  );
}

function PlanComparison({ review, isEnglish }: { review: WorkoutReviewMemberDetail; isEnglish: boolean }) {
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const current = firstExerciseName(review.source_plan, isEnglish);
  const proposed = review.proposed_plan === null ? null : firstExerciseName(review.proposed_plan, isEnglish);
  return (
    <div className="member-workout-review__comparison" aria-label={l("مقایسه نسخه‌ها", "Version comparison")}>
      <span>
        <small>{l("نسخه فعلی", "Current version")}</small>
        <strong>{current ?? l("برنامه فعلی", "Current plan")}</strong>
      </span>
      <span aria-hidden="true">→</span>
      <span>
        <small>{l("نسخه پیشنهادی", "Proposed version")}</small>
        <strong>{proposed ?? l("پیشنهاد مربی", "Coach proposal")}</strong>
      </span>
    </div>
  );
}

function DifferenceRow({
  difference,
  review,
  isEnglish,
}: {
  difference: WorkoutReviewDifferenceEntry;
  review: WorkoutReviewMemberDetail;
  isEnglish: boolean;
}) {
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const changeLabel = changeLabels[difference.change_type] ?? [difference.change_type, difference.change_type];
  const before = formatDifferenceValue(difference.generated, difference.change_type, review.source_plan, isEnglish);
  const after = formatDifferenceValue(difference.approved, difference.change_type, review.proposed_plan, isEnglish);
  return (
    <li>
      <div className="member-workout-review__difference-heading">
        <strong>{changeLabel[isEnglish ? 1 : 0]}</strong>
        <span>{l(`روز ${toLocaleNumber(difference.day_number, false)} · حرکت ${toLocaleNumber(difference.order_index, false)}`, `Day ${difference.day_number} · Exercise ${difference.order_index}`)}</span>
      </div>
      <div className="member-workout-review__before-after">
        <span><small>{l("قبل", "Before")}</small><b>{before}</b></span>
        <span aria-hidden="true">→</span>
        <span><small>{l("بعد", "After")}</small><b>{after}</b></span>
      </div>
    </li>
  );
}

function formatDifferenceValue(
  value: unknown,
  changeType: string,
  plan: WorkoutPlan | null,
  isEnglish: boolean,
): string {
  if (changeType === "exercise_changed") {
    const id = typeof value === "string" ? value : null;
    return exerciseName(plan, id, isEnglish) ?? id ?? "—";
  }
  if (changeType === "exercise_added" || changeType === "exercise_removed") {
    const record = asRecord(value);
    const id = record?.exercise_id === undefined ? null : String(record.exercise_id);
    return exerciseName(plan, id, isEnglish) ?? id ?? (isEnglish ? "Exercise" : "حرکت");
  }
  if (changeType === "day_added" || changeType === "day_removed") {
    const record = asRecord(value);
    if (record !== null) {
      const title = isEnglish ? record.title_en : record.title_fa;
      return typeof title === "string" && title.length > 0 ? title : (isEnglish ? "Day" : "روز");
    }
    return isEnglish ? "Day" : "روز";
  }
  if (changeType === "day_title_changed") {
    const record = asRecord(value);
    const title = isEnglish ? record?.title_en : record?.title_fa;
    return typeof title === "string" && title.length > 0 ? title : "—";
  }
  if (changeType === "notes_changed") {
    const record = asRecord(value);
    const note = isEnglish ? record?.en : record?.fa;
    return typeof note === "string" && note.length > 0 ? note : (isEnglish ? "No note" : "بدون یادداشت");
  }
  if (changeType === "reps_range_changed") {
    const record = asRecord(value);
    const minimum = typeof record?.min === "number" ? record.min : null;
    const maximum = typeof record?.max === "number" ? record.max : null;
    return minimum !== null && maximum !== null
      ? `${toLocaleNumber(minimum, isEnglish)}–${toLocaleNumber(maximum, isEnglish)} ${isEnglish ? "reps" : "تکرار"}`
      : "—";
  }
  if (changeType === "prescription_changed") {
    const record = asRecord(value);
    const mode = record?.mode;
    if (mode === "duration") {
      const minimum = typeof record?.duration_min_seconds === "number" ? record.duration_min_seconds : null;
      const maximum = typeof record?.duration_max_seconds === "number" ? record.duration_max_seconds : null;
      return minimum !== null && maximum !== null
        ? `${toLocaleNumber(minimum, isEnglish)}–${toLocaleNumber(maximum, isEnglish)} ${isEnglish ? "sec" : "ثانیه"}`
        : (isEnglish ? "Duration" : "زمانی");
    }
    return isEnglish ? "Repetitions" : "تکراری";
  }
  if (typeof value === "number") {
    if (changeType === "rest_changed") return `${toLocaleNumber(value, isEnglish)} ${isEnglish ? "sec" : "ثانیه"}`;
    return toLocaleNumber(value, isEnglish);
  }
  if (typeof value === "string") return value;
  if (value === null || value === undefined) return "—";
  return JSON.stringify(value);
}

function asRecord(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null ? value as Record<string, unknown> : null;
}

function firstExerciseName(plan: WorkoutPlan, isEnglish: boolean): string | null {
  const exercise = plan.days[0]?.exercises[0];
  return exercise === undefined ? null : isEnglish ? exercise.exercise.name_en : exercise.exercise.name_fa;
}

function exerciseName(plan: WorkoutPlan | null, exerciseId: string | null, isEnglish: boolean): string | null {
  if (plan === null || exerciseId === null) return null;
  for (const day of plan.days) {
    const exercise = day.exercises.find((item) => item.exercise.id === exerciseId);
    if (exercise !== undefined) return isEnglish ? exercise.exercise.name_en : exercise.exercise.name_fa;
  }
  return null;
}

function formatExerciseTarget(exercise: WorkoutPlanExercise, isEnglish: boolean): string {
  const number = (value: number) => toLocaleNumber(value, isEnglish);
  if (exercise.prescription_mode === "duration") {
    const minimum = exercise.duration_min_seconds ?? 0;
    const maximum = exercise.duration_max_seconds ?? minimum;
    return `${number(exercise.sets)} × ${number(minimum)}–${number(maximum)} ${isEnglish ? "sec" : "ثانیه"}`;
  }
  const minimum = exercise.reps_min ?? 0;
  const maximum = exercise.reps_max ?? minimum;
  return `${number(exercise.sets)} × ${number(minimum)}–${number(maximum)} ${isEnglish ? "reps" : "تکرار"}`;
}

function formatCount(value: number, isEnglish: boolean): string {
  return value.toLocaleString(isEnglish ? "en-US" : "fa-IR", { useGrouping: false });
}

function toLocaleNumber(value: number, isEnglish: boolean): string {
  return value.toLocaleString(isEnglish ? "en-US" : "fa-IR", { useGrouping: false });
}
