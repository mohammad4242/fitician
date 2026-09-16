import { useState } from "react";

import { ReviewDisclosure } from "../../shared/ReviewDisclosure";
import { ReviewProfileSummaryCard } from "../../shared/ReviewProfileSummaryCard";
import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import {
  SpecialistCaseHeader,
  SpecialistCaseTabs,
  SpecialistStatusBadge,
} from "../../shared/specialistWorkbench";
import type {
  CoachTemplateSelection,
  WorkoutReviewDayDraft,
  WorkoutReviewDetail,
  WorkoutReviewExerciseDraft,
} from "./types";

type CoachCaseTab = "summary" | "profile" | "workout" | "feedback" | "notes";

type CoachReviewCaseProps = {
  readonly busy: boolean;
  readonly coachNote: string;
  readonly draft: readonly WorkoutReviewDayDraft[];
  readonly error: string | null;
  readonly fa: boolean;
  readonly onAddDay: () => void;
  readonly onAddExercise: (dayIndex: number) => void;
  readonly onApprove: () => void;
  readonly onBack: () => void;
  readonly onCoachNoteChange: (value: string) => void;
  readonly onMoveDay: (dayIndex: number, direction: -1 | 1) => void;
  readonly onMoveExercise: (dayIndex: number, exerciseIndex: number, direction: -1 | 1) => void;
  readonly onReject: () => void;
  readonly onRemoveDay: (dayIndex: number) => void;
  readonly onRemoveExercise: (dayIndex: number, exerciseIndex: number) => void;
  readonly onSaveDraft: () => void;
  readonly onUpdateDay: (dayIndex: number, patch: Partial<WorkoutReviewDayDraft>) => void;
  readonly onUpdateExercise: (dayIndex: number, exerciseIndex: number, patch: Partial<WorkoutReviewExerciseDraft>) => void;
  readonly selected: WorkoutReviewDetail;
};

const tabs: Array<{ id: CoachCaseTab; fa: string; en: string }> = [
  { id: "summary", fa: "خلاصه", en: "Summary" },
  { id: "profile", fa: "پروفایل و محدودیت‌ها", en: "Profile & limits" },
  { id: "workout", fa: "برنامه تمرینی", en: "Workout plan" },
  { id: "feedback", fa: "بازخورد و سوابق", en: "Feedback & history" },
  { id: "notes", fa: "یادداشت مربی", en: "Coach notes" },
];

export function CoachReviewCase({
  busy,
  coachNote,
  draft,
  error,
  fa,
  onAddDay,
  onAddExercise,
  onApprove,
  onBack,
  onCoachNoteChange,
  onMoveDay,
  onMoveExercise,
  onReject,
  onRemoveDay,
  onRemoveExercise,
  onSaveDraft,
  onUpdateDay,
  onUpdateExercise,
  selected,
}: CoachReviewCaseProps) {
  const [activeTab, setActiveTab] = useState<CoachCaseTab>("summary");
  const readOnly = selected.status === "approved"
    || selected.status === "rejected"
    || selected.status === "awaiting_member_acceptance";
  const memberName = selected.member_display_name ?? (fa ? "کاربر فیتیشن" : "Fitician member");

  return (
    <article className="coach-review-case" data-testid="coach-review-case">
      <div className="coach-review-case-header" data-testid="coach-review-case-header">
        <SpecialistCaseHeader
          avatar={<ProfilePhotoAvatar label={memberName} size="md" url={selected.member_profile_photo_url} />}
          backLabel={fa ? "بازگشت به صف" : "Back to queue"}
          context="coach"
          eyebrow={fa ? "پرونده تمرینی" : "Workout case"}
          fa={fa}
          meta={[
            { label: fa ? "هدف" : "Goal", value: humanize(selected.fitness_goal, fa) },
            { label: fa ? "سطح" : "Experience", value: humanize(selected.experience_level, fa) },
            { label: fa ? "مدت برنامه" : "Plan duration", value: `${selected.source_plan.plan_duration_weeks} ${fa ? "هفته" : "weeks"}` },
          ]}
          name={memberName}
          onBack={onBack}
          status={selected.status}
        />
      </div>

      <SpecialistCaseTabs
        activeTab={activeTab}
        ariaLabel={fa ? "بخش‌های پرونده تمرینی" : "Workout case sections"}
        className="coach-review-case-tabs"
        fa={fa}
        onChange={setActiveTab}
        panelIdPrefix="coach-case-panel"
        tabIdPrefix="coach-case-tab"
        tabs={tabs.map((tab) => ({ id: tab.id, label: fa ? tab.fa : tab.en }))}
      />

      <section
        aria-labelledby={`coach-case-tab-${activeTab}`}
        className="coach-review-case-panel"
        id={`coach-case-panel-${activeTab}`}
        role="tabpanel"
        tabIndex={0}
      >
        {activeTab === "summary" && <CoachCaseSummary fa={fa} selected={selected} />}
        {activeTab === "profile" && <ReviewProfileSummaryCard fa={fa} summary={selected.profile_summary} />}
        {activeTab === "workout" && (
          <CoachWorkoutEditor
            busy={busy}
            draft={draft}
            error={error}
            fa={fa}
            onAddDay={onAddDay}
            onAddExercise={onAddExercise}
            onMoveDay={onMoveDay}
            onMoveExercise={onMoveExercise}
            onRemoveDay={onRemoveDay}
            onRemoveExercise={onRemoveExercise}
            onUpdateDay={onUpdateDay}
            onUpdateExercise={onUpdateExercise}
            readOnly={readOnly}
            selected={selected}
          />
        )}
        {activeTab === "feedback" && <CoachFeedback fa={fa} selected={selected} />}
        {activeTab === "notes" && (
          <CoachNotes
            busy={busy}
            coachNote={coachNote}
            fa={fa}
            onApprove={onApprove}
            onCoachNoteChange={onCoachNoteChange}
            onReject={onReject}
            onSaveDraft={onSaveDraft}
            readOnly={readOnly}
          />
        )}
      </section>
    </article>
  );
}

function CoachCaseSummary({ fa, selected }: { readonly fa: boolean; readonly selected: WorkoutReviewDetail }) {
  return (
    <div className="coach-review-case-summary">
      <ReviewProfileSummaryCard fa={fa} summary={selected.profile_summary} />
      <div className="coach-review-summary-grid">
        <section className="coach-review-summary-section">
          <h3>{fa ? "وضعیت برنامه" : "Plan status"}</h3>
          <dl className="coach-review-key-values">
            <div><dt>{fa ? "مدت" : "Duration"}</dt><dd>{selected.source_plan.plan_duration_weeks} {fa ? "هفته" : "weeks"}</dd></div>
            <div><dt>{fa ? "روزهای برنامه" : "Workout days"}</dt><dd>{selected.source_plan.days.length.toLocaleString(fa ? "fa-IR" : "en-US")}</dd></div>
            <div><dt>{fa ? "نسخه پیش‌نویس" : "Draft revision"}</dt><dd>{selected.draft_revision.toLocaleString(fa ? "fa-IR" : "en-US")}</dd></div>
          </dl>
        </section>
        {selected.template_selection ? <TemplateSelectionAudit fa={fa} selection={selected.template_selection} /> : null}
      </div>
      {selected.member_rejection_note ? (
        <aside className="coach-review-member-feedback" role="status">
          <strong>{fa ? "درخواست اصلاح کاربر" : "Member correction request"}</strong>
          <p>{selected.member_rejection_note}</p>
        </aside>
      ) : null}
    </div>
  );
}

function CoachFeedback({ fa, selected }: { readonly fa: boolean; readonly selected: WorkoutReviewDetail }) {
  return (
    <div className="coach-review-feedback-tab">
      <section className="coach-review-summary-section">
        <h3>{fa ? "بازخورد و سوابق پرونده" : "Case feedback and history"}</h3>
        {selected.member_rejection_note ? (
          <div className="coach-review-feedback-note">
            <SpecialistStatusBadge context="coach" fa={fa} status="member_changes_requested" />
            <p>{selected.member_rejection_note}</p>
          </div>
        ) : (
          <p className="coach-review-empty-state">{fa ? "بازخوردی برای این پرونده ثبت نشده است." : "No member feedback has been recorded."}</p>
        )}
      </section>
      <section className="coach-review-summary-section">
        <h3>{fa ? "نسخه مرجع" : "Reference version"}</h3>
        <p>{fa ? "نسخه اولیه برای مقایسه در کنار پیش‌نویس مربی نگه داشته شده است." : "The initial version is retained as the reference beside the coach draft."}</p>
      </section>
    </div>
  );
}

function CoachNotes({
  busy,
  coachNote,
  fa,
  onApprove,
  onCoachNoteChange,
  onReject,
  onSaveDraft,
  readOnly,
}: {
  readonly busy: boolean;
  readonly coachNote: string;
  readonly fa: boolean;
  readonly onApprove: () => void;
  readonly onCoachNoteChange: (value: string) => void;
  readonly onReject: () => void;
  readonly onSaveDraft: () => void;
  readonly readOnly: boolean;
}) {
  return (
    <div className="coach-review-notes-tab">
      <section className="coach-review-summary-section">
        <h3>{fa ? "یادداشت مربی برای کاربر" : "Coach note for the member"}</h3>
        <label className="coach-review-note">
          <span>{fa ? "این یادداشت همراه نسخه برای کاربر ارسال می‌شود." : "This note is sent with the version to the member."}</span>
          <textarea
            aria-label={fa ? "یادداشت مربی برای کاربر" : "Coach note for the member"}
            disabled={busy || readOnly}
            maxLength={2000}
            onChange={(event) => onCoachNoteChange(event.target.value)}
            value={coachNote}
          />
        </label>
      </section>
      {!readOnly ? (
        <footer className="coach-review-actions" aria-label={fa ? "تصمیم نهایی" : "Final decision"}>
          <h3>{fa ? "تصمیم نهایی" : "Final decision"}</h3>
          <div>
            <button disabled={busy} onClick={onSaveDraft} type="button">{fa ? "ذخیره پیش‌نویس" : "Save draft"}</button>
            <button className="is-reject" disabled={busy || !coachNote.trim()} onClick={onReject} type="button">{fa ? "برگشت برای اصلاح" : "Return for correction"}</button>
            <button className="is-primary" disabled={busy} onClick={onApprove} type="button">{fa ? "ارسال برای تأیید کاربر" : "Send for member approval"}</button>
          </div>
        </footer>
      ) : null}
    </div>
  );
}

function CoachWorkoutEditor({
  busy,
  draft,
  error,
  fa,
  onAddDay,
  onAddExercise,
  onMoveDay,
  onMoveExercise,
  onRemoveDay,
  onRemoveExercise,
  onUpdateDay,
  onUpdateExercise,
  readOnly,
  selected,
}: {
  readonly busy: boolean;
  readonly draft: readonly WorkoutReviewDayDraft[];
  readonly error: string | null;
  readonly fa: boolean;
  readonly onAddDay: () => void;
  readonly onAddExercise: (dayIndex: number) => void;
  readonly onMoveDay: (dayIndex: number, direction: -1 | 1) => void;
  readonly onMoveExercise: (dayIndex: number, exerciseIndex: number, direction: -1 | 1) => void;
  readonly onRemoveDay: (dayIndex: number) => void;
  readonly onRemoveExercise: (dayIndex: number, exerciseIndex: number) => void;
  readonly onUpdateDay: (dayIndex: number, patch: Partial<WorkoutReviewDayDraft>) => void;
  readonly onUpdateExercise: (dayIndex: number, exerciseIndex: number, patch: Partial<WorkoutReviewExerciseDraft>) => void;
  readonly readOnly: boolean;
  readonly selected: WorkoutReviewDetail;
}) {
  return (
    <div className="coach-review-workout-tab">
      <div className="coach-review-version-labels">
        <span>{fa ? "نسخه اولیه — فقط خواندنی" : "Initial version — read only"}</span>
        <span>{readOnly ? fa ? "نسخه تأییدشده" : "Approved version" : fa ? "پیش‌نویس مربی" : "Coach draft"}</span>
      </div>
      {!readOnly ? (
        <div className="coach-review-structure-toolbar">
          <span>{fa ? "ساختار برنامه را کامل ویرایش کن" : "Edit the full plan structure"}</span>
          <button disabled={busy || draft.length >= 6 || selected.exercise_options.length === 0} onClick={onAddDay} type="button">
            {fa ? "افزودن روز" : "Add day"}
          </button>
        </div>
      ) : null}
      {error ? <p className="coach-review-editor-error" role="alert">{error}</p> : null}
      <div className="coach-review-days">
        {draft.map((day, dayIndex) => (
          <ReviewDisclosure
            className="coach-review-day"
            key={day.day_number}
            section="coach-workout-day"
            summary={fa ? `${faNumber(day.exercises.length)} حرکت` : `${day.exercises.length} exercises`}
            title={fa ? day.title_fa || `روز ${faNumber(day.day_number)}` : day.title_en || `Day ${day.day_number}`}
          >
            {!readOnly ? (
              <div className="coach-review-day-tools">
                <div className="coach-review-day-titles">
                  <label>
                    {fa ? `عنوان فارسی روز ${faNumber(day.day_number)}` : `Persian title for day ${day.day_number}`}
                    <input
                      aria-label={fa ? `عنوان فارسی روز ${faNumber(day.day_number)}` : `Persian title for day ${day.day_number}`}
                      onChange={(event) => onUpdateDay(dayIndex, { title_fa: event.target.value || null })}
                      value={day.title_fa ?? ""}
                    />
                  </label>
                  <label>
                    {fa ? `عنوان انگلیسی روز ${faNumber(day.day_number)}` : `English title for day ${day.day_number}`}
                    <input
                      aria-label={fa ? `عنوان انگلیسی روز ${faNumber(day.day_number)}` : `English title for day ${day.day_number}`}
                      dir="ltr"
                      onChange={(event) => onUpdateDay(dayIndex, { title_en: event.target.value || null })}
                      value={day.title_en ?? ""}
                    />
                  </label>
                </div>
                <div className="coach-review-inline-actions">
                  <button aria-label={fa ? `روز ${faNumber(day.day_number)} را بالا ببر` : `Move day ${day.day_number} up`} disabled={busy || dayIndex === 0} onClick={() => onMoveDay(dayIndex, -1)} type="button">↑</button>
                  <button aria-label={fa ? `روز ${faNumber(day.day_number)} را پایین ببر` : `Move day ${day.day_number} down`} disabled={busy || dayIndex === draft.length - 1} onClick={() => onMoveDay(dayIndex, 1)} type="button">↓</button>
                  <button aria-label={fa ? `حذف روز ${faNumber(day.day_number)}` : `Remove day ${day.day_number}`} className="is-danger" disabled={busy || draft.length <= 1} onClick={() => onRemoveDay(dayIndex)} type="button">{fa ? "حذف روز" : "Remove day"}</button>
                </div>
              </div>
            ) : null}
            {day.exercises.map((exercise, exerciseIndex) => {
              const exerciseOption = selected.exercise_options.find((option) => option.id === exercise.exercise_id);
              const exerciseName = exerciseOption ? fa ? exerciseOption.name_fa : exerciseOption.name_en : fa ? `حرکت ${faNumber(exercise.order_index)}` : `Exercise ${exercise.order_index}`;
              const exerciseTitle = exerciseOption ? fa ? `حرکت ${faNumber(exercise.order_index)} · ${exerciseName}` : `Exercise ${exercise.order_index} · ${exerciseName}` : exerciseName;
              const labelSuffix = fa ? `روز ${faNumber(day.day_number)} حرکت ${faNumber(exercise.order_index)}` : `day ${day.day_number} exercise ${exercise.order_index}`;
              return (
                <ReviewDisclosure className="coach-review-exercise" key={exercise.order_index} section="coach-workout-exercise" summary={fa ? `${faNumber(exercise.sets)} ست` : `${exercise.sets} sets`} title={exerciseTitle}>
                  {!readOnly ? (
                    <div className="coach-review-exercise-tools">
                      <button aria-label={fa ? `حرکت ${faNumber(exercise.order_index)} از روز ${faNumber(day.day_number)} را بالا ببر` : `Move exercise ${exercise.order_index} in day ${day.day_number} up`} disabled={busy || exerciseIndex === 0} onClick={() => onMoveExercise(dayIndex, exerciseIndex, -1)} type="button">↑</button>
                      <button aria-label={fa ? `حرکت ${faNumber(exercise.order_index)} از روز ${faNumber(day.day_number)} را پایین ببر` : `Move exercise ${exercise.order_index} in day ${day.day_number} down`} disabled={busy || exerciseIndex === day.exercises.length - 1} onClick={() => onMoveExercise(dayIndex, exerciseIndex, 1)} type="button">↓</button>
                      <button aria-label={fa ? `حرکت ${faNumber(exercise.order_index)} از روز ${faNumber(day.day_number)} را حذف کن` : `Remove exercise ${exercise.order_index} from day ${day.day_number}`} className="is-danger" disabled={busy || day.exercises.length <= 1} onClick={() => onRemoveExercise(dayIndex, exerciseIndex)} type="button">{fa ? "حذف حرکت" : "Remove exercise"}</button>
                    </div>
                  ) : null}
                  <fieldset disabled={busy || readOnly}>
                    <legend>{fa ? `حرکت ${faNumber(exercise.order_index)}` : `Exercise ${exercise.order_index}`}</legend>
                    <label>
                      {fa ? "انتخاب حرکت" : "Exercise"}
                      <select onChange={(event) => updateExerciseSelection(selected, onUpdateExercise, dayIndex, exerciseIndex, event.target.value)} value={exercise.exercise_id}>
                        {selected.exercise_options.map((option) => <option key={option.id} value={option.id}>{fa ? option.name_fa : option.name_en}</option>)}
                      </select>
                    </label>
                    <div className="coach-review-prescription">
                      <NumberField label={fa ? `تعداد ست ${labelSuffix}` : `Sets ${labelSuffix}`} onChange={(sets) => onUpdateExercise(dayIndex, exerciseIndex, { sets })} value={exercise.sets} />
                      {exercise.prescription_mode === "duration" ? (
                        <>
                          <NumberField label={fa ? `حداقل ثانیه ${labelSuffix}` : `Minimum seconds ${labelSuffix}`} onChange={(duration_min_seconds) => onUpdateExercise(dayIndex, exerciseIndex, { duration_min_seconds })} value={exercise.duration_min_seconds ?? 0} />
                          <NumberField label={fa ? `حداکثر ثانیه ${labelSuffix}` : `Maximum seconds ${labelSuffix}`} onChange={(duration_max_seconds) => onUpdateExercise(dayIndex, exerciseIndex, { duration_max_seconds })} value={exercise.duration_max_seconds ?? 0} />
                        </>
                      ) : (
                        <>
                          <NumberField label={fa ? `حداقل تکرار ${labelSuffix}` : `Minimum reps ${labelSuffix}`} onChange={(reps_min) => onUpdateExercise(dayIndex, exerciseIndex, { reps_min })} value={exercise.reps_min ?? 8} />
                          <NumberField label={fa ? `حداکثر تکرار ${labelSuffix}` : `Maximum reps ${labelSuffix}`} onChange={(reps_max) => onUpdateExercise(dayIndex, exerciseIndex, { reps_max })} value={exercise.reps_max ?? 12} />
                          <NumberField label={`RIR ${labelSuffix}`} max={5} min={0} onChange={(rir) => onUpdateExercise(dayIndex, exerciseIndex, { rir })} value={exercise.rir ?? 2} />
                        </>
                      )}
                      <NumberField label={fa ? `استراحت ${labelSuffix}` : `Rest ${labelSuffix}`} onChange={(rest_seconds) => onUpdateExercise(dayIndex, exerciseIndex, { rest_seconds })} step={15} value={exercise.rest_seconds} />
                    </div>
                    <label>
                      {fa ? "یادداشت فارسی حرکت" : "Persian exercise note"}
                      <textarea onChange={(event) => onUpdateExercise(dayIndex, exerciseIndex, { notes_fa: event.target.value || null })} value={exercise.notes_fa ?? ""} />
                    </label>
                    <label>
                      {fa ? "یادداشت انگلیسی حرکت" : "English exercise note"}
                      <textarea dir="ltr" onChange={(event) => onUpdateExercise(dayIndex, exerciseIndex, { notes_en: event.target.value || null })} value={exercise.notes_en ?? ""} />
                    </label>
                  </fieldset>
                </ReviewDisclosure>
              );
            })}
            {!readOnly ? <button className="coach-review-add-exercise" disabled={busy || day.exercises.length >= 10} onClick={() => onAddExercise(dayIndex)} type="button">{fa ? `افزودن حرکت به روز ${faNumber(day.day_number)}` : `Add exercise to day ${day.day_number}`}</button> : null}
          </ReviewDisclosure>
        ))}
      </div>
    </div>
  );
}

function TemplateSelectionAudit({ fa, selection }: { readonly fa: boolean; readonly selection: CoachTemplateSelection }) {
  const scores = [
    [fa ? "اولویت عضلانی" : "Priority", selection.score.priority],
    [fa ? "آنالیز بدن" : "Body Analysis", selection.score.body_analysis],
    [fa ? "هدف" : "Goal", selection.score.goal],
    [fa ? "پیش‌فرض جنسیتی" : "Sex prior", selection.score.sex],
    [fa ? "ساختار متعادل" : "Fallback", selection.score.fallback],
    [fa ? "مجموع" : "Total", selection.score.total],
  ] as const;
  const number = new Intl.NumberFormat(fa ? "fa-IR" : "en");

  return (
    <section className="coach-template-selection">
      <ReviewDisclosure className="coach-template-disclosure" section="coach-rationale" summary={fa ? selection.explanation_fa : selection.explanation_en} title={fa ? "علت انتخاب برنامه" : "Why this program was selected"}>
        <details>
          <summary>{fa ? "جزئیات امتیازدهی" : "Scoring details"}</summary>
          <div className="coach-template-selection-details">
            <div className="coach-template-slug"><span>{fa ? "قالب منتخب" : "Selected template"}</span><code dir="ltr">{selection.selected_template}</code></div>
            <dl>
              {scores.map(([label, value]) => <div className={label === (fa ? "مجموع" : "Total") ? "is-total" : undefined} key={label}><dt>{label}</dt><dd>{number.format(value)}</dd></div>)}
            </dl>
          </div>
        </details>
      </ReviewDisclosure>
    </section>
  );
}

function NumberField({
  label,
  max,
  min = 1,
  onChange,
  step = 1,
  value,
}: {
  readonly label: string;
  readonly max?: number;
  readonly min?: number;
  readonly onChange: (value: number) => void;
  readonly step?: number;
  readonly value: number;
}) {
  return <label>{label}<input aria-label={label} max={max} min={min} onChange={(event) => onChange(Number(event.target.value))} step={step} type="number" value={value} /></label>;
}

function updateExerciseSelection(
  selected: WorkoutReviewDetail,
  onUpdateExercise: CoachReviewCaseProps["onUpdateExercise"],
  dayIndex: number,
  exerciseIndex: number,
  exerciseId: string,
) {
  const option = selected.exercise_options.find((item) => item.id === exerciseId);
  if (option?.prescription_mode === "duration") {
    onUpdateExercise(dayIndex, exerciseIndex, {
      duration_max_seconds: option.duration_max_seconds ?? null,
      duration_min_seconds: option.duration_min_seconds ?? null,
      exercise_id: exerciseId,
      prescription_mode: "duration",
      reps_max: null,
      reps_min: null,
      rir: null,
    });
    return;
  }
  onUpdateExercise(dayIndex, exerciseIndex, {
    duration_max_seconds: null,
    duration_min_seconds: null,
    exercise_id: exerciseId,
    prescription_mode: "reps",
    reps_max: 12,
    reps_min: 8,
    rir: 2,
  });
}

function humanize(value: string | null, fa: boolean) {
  if (!value) return fa ? "ثبت نشده" : "Not provided";
  const labels: Record<string, [string, string]> = {
    advanced: ["پیشرفته", "Advanced"],
    beginner: ["مبتدی", "Beginner"],
    build_muscle: ["عضله‌سازی", "Build muscle"],
    intermediate: ["متوسط", "Intermediate"],
    lose_weight: ["کاهش وزن", "Lose weight"],
  };
  return labels[value]?.[fa ? 0 : 1] ?? value.replaceAll("_", " ");
}

function faNumber(value: number) {
  return value.toLocaleString("fa-IR", { useGrouping: false });
}
