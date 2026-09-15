import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";

import {
  formatTehranDateTime,
  formatTehranDateTimeForLocale,
  formatTehranTimeForLocale,
  groupWorkoutReviewQueue,
} from "@fitician/core";
import { AuthenticatedHeader } from "../../shared/AuthenticatedHeader";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { ProfilePhotoAvatar } from "../profile/ProfilePhoto";
import { ReviewDisclosure } from "../../shared/ReviewDisclosure";
import { ReviewProfileSummaryCard } from "../../shared/ReviewProfileSummaryCard";
import { ReviewQueueGroupHeader } from "../../shared/ReviewQueueGroupHeader";
import {
  approveWorkoutReview,
  claimWorkoutReview,
  getWorkoutReview,
  listWorkoutReviews,
  rejectWorkoutReview,
  renewWorkoutReview,
  saveWorkoutReviewDraft,
} from "./api";
import type {
  CoachTemplateSelection,
  WorkoutReviewDayDraft,
  WorkoutReviewDetail,
  WorkoutReviewExerciseDraft,
  WorkoutReviewQueueItem,
  WorkoutReviewQueueView,
} from "./types";
import "./coachWorkoutReview.css";

const queueViews: WorkoutReviewQueueView[] = ["pending", "mine", "approved"];

export function CoachWorkoutReviewPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const fa = i18n.resolvedLanguage !== "en";
  const l = useCallback((faText: string, enText: string) => (fa ? faText : enText), [fa]);
  const [view, setView] = useState<WorkoutReviewQueueView>("pending");
  const [queue, setQueue] = useState<WorkoutReviewQueueItem[]>([]);
  const [selected, setSelected] = useState<WorkoutReviewDetail | null>(null);
  const [draft, setDraft] = useState<WorkoutReviewDayDraft[]>([]);
  const [coachNote, setCoachNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<unknown>(null);
  const readOnly = selected?.status === "approved"
    || selected?.status === "rejected"
    || selected?.status === "awaiting_member_acceptance";
  const groupedQueue = useMemo(
    () => groupWorkoutReviewQueue(queue, new Date().toISOString(), view === "approved" ? "approved_at" : "created_at"),
    [queue, view],
  );

  const loadQueue = useCallback(async (nextView: WorkoutReviewQueueView) => {
    setLoading(true);
    setApiError(null);
    try {
      setQueue(await listWorkoutReviews(nextView));
    } catch (cause) {
      setApiError(cause);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadQueue(view);
  }, [loadQueue, view]);

  useEffect(() => {
    if (selected?.status !== "claimed") return;
    const timer = window.setInterval(() => {
      void renewWorkoutReview(selected.id)
        .then((updated) => setSelected(updated))
        .catch((cause) => setApiError(cause));
    }, 8 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, [l, selected?.id, selected?.status]);

  function openDetail(detail: WorkoutReviewDetail) {
    setSelected(detail);
    setDraft(structuredClone(detail.draft?.days ?? []));
    setCoachNote(detail.coach_note ?? "");
    setError(null);
    setApiError(null);
  }

  function clearSelectedReview() {
    setSelected(null);
    setDraft([]);
    setCoachNote("");
    setError(null);
    setApiError(null);
  }

  async function openReview(item: WorkoutReviewQueueItem) {
    setBusy(true);
    setError(null);
    setApiError(null);
    try {
      const nextView = item.status === "pending" ? "mine" : view;
      openDetail(
        item.status === "pending"
          ? await claimWorkoutReview(item.id)
          : await getWorkoutReview(item.id),
      );
      if (nextView !== view) setView(nextView);
      await loadQueue(nextView);
    } catch (cause) {
      await loadQueue(view);
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  function updateExercise(
    dayIndex: number,
    exerciseIndex: number,
    patch: Partial<WorkoutReviewExerciseDraft>,
  ) {
    setDraft((current) => current.map((day, index) => index !== dayIndex ? day : {
      ...day,
      exercises: day.exercises.map((exercise, itemIndex) => (
        itemIndex === exerciseIndex ? { ...exercise, ...patch } : exercise
      )),
    }));
  }

  function updateDay(dayIndex: number, patch: Partial<WorkoutReviewDayDraft>) {
    setDraft((current) => current.map((day, index) => (
      index === dayIndex ? { ...day, ...patch } : day
    )));
  }

  function addDay() {
    if (!selected?.exercise_options.length) {
      setError(l("حرکتی برای افزودن وجود ندارد.", "No exercise is available to add."));
      return;
    }
    if (draft.length >= 6) {
      setError(l("حداکثر ۶ روز مجاز است.", "A plan can have at most 6 days."));
      return;
    }
    const dayNumber = draft.length + 1;
    setError(null);
    setDraft((current) => [
      ...current,
      {
        day_number: dayNumber,
        title_en: null,
        title_fa: null,
        exercises: [newExerciseDraft(1, selected?.exercise_options[0])],
      },
    ]);
  }

  function removeDay(dayIndex: number) {
    if (draft.length <= 1) {
      setError(l("برای حذف آخرین روز، ابتدا یک روز دیگر اضافه کن.", "Keep at least one workout day."));
      return;
    }
    setError(null);
    setDraft((current) => renumberDays(current.filter((_, index) => index !== dayIndex)));
  }

  function moveDay(dayIndex: number, direction: -1 | 1) {
    const targetIndex = dayIndex + direction;
    if (targetIndex < 0 || targetIndex >= draft.length) return;
    setError(null);
    setDraft((current) => {
      const next = [...current];
      const [moved] = next.splice(dayIndex, 1);
      if (!moved) return current;
      next.splice(targetIndex, 0, moved);
      return renumberDays(next);
    });
  }

  function addExercise(dayIndex: number) {
    if (!selected?.exercise_options.length) {
      setError(l("حرکتی برای افزودن وجود ندارد.", "No exercise is available to add."));
      return;
    }
    if (draft[dayIndex]?.exercises.length >= 10) {
      setError(l("حداکثر ۱۰ حرکت در هر روز مجاز است.", "A day can have at most 10 exercises."));
      return;
    }
    setError(null);
    setDraft((current) => current.map((day, index) => {
      if (index !== dayIndex) return day;
      return {
        ...day,
        exercises: [
          ...day.exercises,
          newExerciseDraft(day.exercises.length + 1, selected?.exercise_options[0]),
        ],
      };
    }));
  }

  function removeExercise(dayIndex: number, exerciseIndex: number) {
    const day = draft[dayIndex];
    if (!day || day.exercises.length <= 1) {
      setError(l("برای حذف آخرین حرکت، روز را حذف کن.", "Remove the day to remove its last exercise."));
      return;
    }
    setError(null);
    setDraft((current) => current.map((item, index) => {
      if (index !== dayIndex) return item;
      return {
        ...item,
        exercises: renumberExercises(item.exercises.filter((_, itemIndex) => itemIndex !== exerciseIndex)),
      };
    }));
  }

  function moveExercise(dayIndex: number, exerciseIndex: number, direction: -1 | 1) {
    const day = draft[dayIndex];
    if (!day) return;
    const targetIndex = exerciseIndex + direction;
    if (targetIndex < 0 || targetIndex >= day.exercises.length) return;
    setError(null);
    setDraft((current) => current.map((item, index) => {
      if (index !== dayIndex) return item;
      const exercises = [...item.exercises];
      const [moved] = exercises.splice(exerciseIndex, 1);
      if (!moved) return item;
      exercises.splice(targetIndex, 0, moved);
      return { ...item, exercises: renumberExercises(exercises) };
    }));
  }

  function updateExerciseSelection(
    dayIndex: number,
    exerciseIndex: number,
    exerciseId: string,
  ) {
    const option = selected?.exercise_options.find((item) => item.id === exerciseId);
    if (option?.prescription_mode === "duration") {
      updateExercise(dayIndex, exerciseIndex, {
        exercise_id: exerciseId,
        prescription_mode: "duration",
        reps_min: null,
        reps_max: null,
        duration_min_seconds: option.duration_min_seconds ?? null,
        duration_max_seconds: option.duration_max_seconds ?? null,
        rir: null,
      });
      return;
    }
    updateExercise(dayIndex, exerciseIndex, {
      exercise_id: exerciseId,
      prescription_mode: "reps",
      reps_min: 8,
      reps_max: 12,
      duration_min_seconds: null,
      duration_max_seconds: null,
      rir: 2,
    });
  }

  async function saveDraft() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setApiError(null);
    try {
      openDetail(await saveWorkoutReviewDraft(selected.id, {
        expected_revision: selected.draft_revision,
        coach_note: coachNote.trim() || null,
        days: draft,
      }));
    } catch (cause) {
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setApiError(null);
    try {
      await approveWorkoutReview(selected.id, selected.draft_revision);
      setSelected(null);
      setDraft([]);
      setView("mine");
      await loadQueue("mine");
    } catch (cause) {
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  async function reject() {
    if (!selected) return;
    const explanation = coachNote.trim();
    if (!explanation) {
      setError(l("برای برگشت برنامه، دلیل اصلاح را بنویس.", "Add an explanation before returning the plan."));
      return;
    }
    setBusy(true);
    setError(null);
    setApiError(null);
    try {
      await rejectWorkoutReview(selected.id, selected.draft_revision, explanation);
      setSelected(null);
      setDraft([]);
      setView("mine");
      await loadQueue("mine");
    } catch (cause) {
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  const leaseLabel = useMemo(() => {
    if (!selected?.lease_expires_at) return l("بدون قفل فعال", "No active lease");
    return formatTehranTimeForLocale(selected.lease_expires_at, fa ? "fa-IR" : "en");
  }, [fa, l, selected?.lease_expires_at]);

  return (
    <div className="coach-review-shell" dir={fa ? "rtl" : "ltr"}>
      <AuthenticatedHeader />
      <main className="coach-review-page">
        <header className="coach-review-hero">
          <button className="coach-review-back" type="button" onClick={() => navigate(-1)}>
            {l("بازگشت", "Back")}
          </button>
          <div>
            <p>{l("میز کار مربی", "Coach desk")}</p>
            <h1 className="fitician-display">{l("بازبینی برنامه‌های تمرینی", "Workout plan reviews")}</h1>
            <span>{l("نسخه اولیه فعال می‌ماند تا نسخه تو با اعتبارسنجی کامل تأیید شود.", "The initial plan stays active until your validated version is approved.")}</span>
          </div>
          <aside className="coach-review-lease" aria-label={l("زمان قفل بازبینی", "Review lease time")}>
            <span aria-hidden="true" />
            <small>{l("قفل بازبینی تا", "Review lease until")}</small>
            <strong>{leaseLabel}</strong>
          </aside>
        </header>

        <AppErrorNotice audience="coach" context="specialist_review" error={apiError} locale={fa ? "fa" : "en"} />
        {error && <p className="coach-review-error" role="alert">{error}</p>}

        <div className={`coach-review-workspace${selected ? " has-selected" : ""}`}>
          <aside className="coach-review-queue">
            <div className="coach-review-tabs" role="tablist" aria-label={l("صف‌های بازبینی", "Review queues")}>
              {queueViews.map((item) => (
                <button
                  key={item}
                  type="button"
                  role="tab"
                  aria-selected={view === item}
                  onClick={() => { setView(item); clearSelectedReview(); }}
                >
                  {queueTitle(item, fa)}
                </button>
              ))}
            </div>
            {loading && <p role="status">{l("در حال دریافت پرونده‌ها…", "Loading cases…")}</p>}
            {!loading && queue.length === 0 && (
              <p className="coach-review-empty">{l("در این صف پرونده‌ای نیست.", "This queue is clear.")}</p>
            )}
            <div className="coach-review-cases">
              {groupedQueue.map((group) => (
                <details
                  aria-labelledby={`coach-review-group-${group.key}`}
                  className="coach-review-group"
                  data-queue-group-key={group.key}
                  key={group.key}
                >
                  <ReviewQueueGroupHeader
                    collapsible
                    count={group.items.length}
                    fa={fa}
                    group={group}
                    headingId={`coach-review-group-${group.key}`}
                  />
                  <div className="coach-review-group-items">
                    {group.items.map((item) => (
                      <article key={item.id} className={selected?.id === item.id ? "is-selected" : undefined}>
                        <div className="coach-review-member">
                          <ProfilePhotoAvatar
                            url={item.member_profile_photo_url}
                            label={item.member_display_name ?? l("کاربر فیتیشن", "Fitician member")}
                            size="sm"
                          />
                          <div className="coach-review-case-copy">
                            <strong>{item.member_display_name ?? l("کاربر فیتیشن", "Fitician member")}</strong>
                            <span>{humanize(item.fitness_goal, fa)} · {humanize(item.experience_level, fa)}</span>
                          </div>
                        </div>
                        <time className="coach-review-sent-at" dateTime={item.created_at}>{sentAtLabel(item.created_at, fa)}</time>
                        {item.approved_at && <time className="coach-review-approved-at" dateTime={item.approved_at}>{approvedAtLabel(item.approved_at, fa)}</time>}
                        <span className="coach-review-case-status">{statusTitle(item.status, fa)}</span>
                        <button type="button" disabled={busy} onClick={() => void openReview(item)}>
                          {item.status === "pending" ? l("شروع بازبینی", "Start review") : l("مشاهده پرونده", "Open case")}
                        </button>
                      </article>
                    ))}
                  </div>
                </details>
              ))}
            </div>
          </aside>

          <section className="coach-review-canvas" aria-live="polite">
            {!selected && (
              <div className="coach-review-placeholder">
                <span aria-hidden="true">↗</span>
                <h2>{l("یک برنامه را از صف انتخاب کن", "Choose a plan from the queue")}</h2>
                <p>{l("پس از گرفتن پرونده، نسخه اولیه و ابزار ویرایش کنار هم نمایش داده می‌شوند.", "After claiming it, the source version and editing tools appear together.")}</p>
              </div>
            )}
            {selected && (
              <>
                <button className="coach-review-mobile-back" type="button" onClick={clearSelectedReview}>
                  {l("بازگشت به صف", "Back to queue")}
                </button>
                <header className="coach-review-case-header">
                  <div>
                    <small>{l("پرونده", "Case")}</small>
                    <div className="coach-review-case-member">
                      <ProfilePhotoAvatar
                        url={selected.member_profile_photo_url}
                        label={selected.member_display_name ?? l("کاربر فیتیشن", "Fitician member")}
                        size="md"
                      />
                      <h2>{selected.member_display_name ?? l("کاربر فیتیشن", "Fitician member")}</h2>
                    </div>
                  </div>
                  <span data-status={selected.status}>{statusTitle(selected.status, fa)}</span>
                </header>

                <div className="coach-review-profile-strip">
                  <span>{l("هدف", "Goal")}<strong>{humanize(selected.fitness_goal, fa)}</strong></span>
                  <span>{l("سابقه", "Experience")}<strong>{humanize(selected.experience_level, fa)}</strong></span>
                  <span>{l("مدت", "Duration")}<strong>{selected.source_plan.plan_duration_weeks} {l("هفته", "weeks")}</strong></span>
                </div>

                <ReviewProfileSummaryCard summary={selected.profile_summary} fa={fa} />

                {selected.member_rejection_note && (
                  <aside className="coach-review-member-feedback" role="status">
                    <strong>{l("درخواست اصلاح کاربر", "Member correction request")}</strong>
                    <p>{selected.member_rejection_note}</p>
                  </aside>
                )}

                {selected.template_selection && (
                  <TemplateSelectionAudit
                    selection={selected.template_selection}
                    fa={fa}
                  />
                )}

                <div className="coach-review-version-labels">
                  <span>{l("نسخه اولیه — فقط خواندنی", "Initial version — read only")}</span>
                  <span>{readOnly ? l("نسخه تأییدشده", "Approved version") : l("پیش‌نویس مربی", "Coach draft")}</span>
                </div>

                {!readOnly && (
                  <div className="coach-review-structure-toolbar">
                    <span>{l("ساختار برنامه را کامل ویرایش کن", "Edit the full plan structure")}</span>
                    <button
                      type="button"
                      disabled={busy || draft.length >= 6 || selected.exercise_options.length === 0}
                      onClick={addDay}
                    >
                      {l("افزودن روز", "Add day")}
                    </button>
                  </div>
                )}

                <div className="coach-review-days">
                  {draft.map((day, dayIndex) => (
                    <ReviewDisclosure
                      className="coach-review-day"
                      key={day.day_number}
                      section="coach-workout-day"
                      summary={l(`${faNumber(day.exercises.length)} حرکت`, `${day.exercises.length} exercises`)}
                      title={fa ? day.title_fa || `روز ${faNumber(day.day_number)}` : day.title_en || `Day ${day.day_number}`}
                    >
                      {!readOnly && (
                        <div className="coach-review-day-tools">
                          <div className="coach-review-day-titles">
                            <label>
                              {l(`عنوان فارسی روز ${faNumber(day.day_number)}`, `Persian title for day ${day.day_number}`)}
                              <input
                                aria-label={l(`عنوان فارسی روز ${faNumber(day.day_number)}`, `Persian title for day ${day.day_number}`)}
                                value={day.title_fa ?? ""}
                                onChange={(event) => updateDay(dayIndex, { title_fa: event.target.value || null })}
                              />
                            </label>
                            <label>
                              {l(`عنوان انگلیسی روز ${faNumber(day.day_number)}`, `English title for day ${day.day_number}`)}
                              <input
                                aria-label={l(`عنوان انگلیسی روز ${faNumber(day.day_number)}`, `English title for day ${day.day_number}`)}
                                dir="ltr"
                                value={day.title_en ?? ""}
                                onChange={(event) => updateDay(dayIndex, { title_en: event.target.value || null })}
                              />
                            </label>
                          </div>
                          <div className="coach-review-inline-actions">
                            <button
                              type="button"
                              aria-label={l(`روز ${faNumber(day.day_number)} را بالا ببر`, `Move day ${day.day_number} up`)}
                              disabled={busy || dayIndex === 0}
                              onClick={() => moveDay(dayIndex, -1)}
                            >↑</button>
                            <button
                              type="button"
                              aria-label={l(`روز ${faNumber(day.day_number)} را پایین ببر`, `Move day ${day.day_number} down`)}
                              disabled={busy || dayIndex === draft.length - 1}
                              onClick={() => moveDay(dayIndex, 1)}
                            >↓</button>
                            <button
                              className="is-danger"
                              type="button"
                              aria-label={l(`حذف روز ${faNumber(day.day_number)}`, `Remove day ${day.day_number}`)}
                              disabled={busy || draft.length <= 1}
                              onClick={() => removeDay(dayIndex)}
                            >{l("حذف روز", "Remove day")}</button>
                          </div>
                        </div>
                      )}
                      {day.exercises.map((exercise, exerciseIndex) => {
                        const exerciseOption = selected.exercise_options.find((option) => option.id === exercise.exercise_id);
                        const exerciseName = exerciseOption
                          ? (fa ? exerciseOption.name_fa : exerciseOption.name_en)
                          : l(`حرکت ${faNumber(exercise.order_index)}`, `Exercise ${exercise.order_index}`);
                        const exerciseTitle = exerciseOption
                          ? l(`حرکت ${faNumber(exercise.order_index)} · ${exerciseName}`, `Exercise ${exercise.order_index} · ${exerciseName}`)
                          : exerciseName;
                        const labelSuffix = l(
                          `روز ${faNumber(day.day_number)} حرکت ${faNumber(exercise.order_index)}`,
                          `day ${day.day_number} exercise ${exercise.order_index}`,
                        );
                        return (
                          <ReviewDisclosure
                            className="coach-review-exercise"
                            key={exercise.order_index}
                            section="coach-workout-exercise"
                            summary={l(`${faNumber(exercise.sets)} ست`, `${exercise.sets} sets`)}
                            title={exerciseTitle}
                          >
                            {!readOnly && (
                              <div className="coach-review-exercise-tools">
                                <button
                                  type="button"
                                  aria-label={l(`حرکت ${faNumber(exercise.order_index)} از روز ${faNumber(day.day_number)} را بالا ببر`, `Move exercise ${exercise.order_index} in day ${day.day_number} up`)}
                                  disabled={busy || exerciseIndex === 0}
                                  onClick={() => moveExercise(dayIndex, exerciseIndex, -1)}
                                >↑</button>
                                <button
                                  type="button"
                                  aria-label={l(`حرکت ${faNumber(exercise.order_index)} از روز ${faNumber(day.day_number)} را پایین ببر`, `Move exercise ${exercise.order_index} in day ${day.day_number} down`)}
                                  disabled={busy || exerciseIndex === day.exercises.length - 1}
                                  onClick={() => moveExercise(dayIndex, exerciseIndex, 1)}
                                >↓</button>
                                <button
                                  className="is-danger"
                                  type="button"
                                  aria-label={l(`حرکت ${faNumber(exercise.order_index)} از روز ${faNumber(day.day_number)} را حذف کن`, `Remove exercise ${exercise.order_index} from day ${day.day_number}`)}
                                  disabled={busy || day.exercises.length <= 1}
                                  onClick={() => removeExercise(dayIndex, exerciseIndex)}
                                >{l("حذف حرکت", "Remove exercise")}</button>
                              </div>
                            )}
                            <fieldset disabled={busy || readOnly}>
                              <legend>{l(`حرکت ${faNumber(exercise.order_index)}`, `Exercise ${exercise.order_index}`)}</legend>
                              <label>
                                {l("انتخاب حرکت", "Exercise")}
                                <select value={exercise.exercise_id} onChange={(event) => updateExerciseSelection(dayIndex, exerciseIndex, event.target.value)}>
                                  {selected.exercise_options.map((option) => (
                                    <option key={option.id} value={option.id}>{fa ? option.name_fa : option.name_en}</option>
                                  ))}
                                </select>
                              </label>
                              <div className="coach-review-prescription">
                                <NumberField label={l(`تعداد ست ${labelSuffix}`, `Sets ${labelSuffix}`)} value={exercise.sets} onChange={(sets) => updateExercise(dayIndex, exerciseIndex, { sets })} />
                                {exercise.prescription_mode === "duration" ? (
                                  <>
                                    <NumberField label={l(`حداقل ثانیه ${labelSuffix}`, `Minimum seconds ${labelSuffix}`)} value={exercise.duration_min_seconds ?? 0} onChange={(duration_min_seconds) => updateExercise(dayIndex, exerciseIndex, { duration_min_seconds })} />
                                    <NumberField label={l(`حداکثر ثانیه ${labelSuffix}`, `Maximum seconds ${labelSuffix}`)} value={exercise.duration_max_seconds ?? 0} onChange={(duration_max_seconds) => updateExercise(dayIndex, exerciseIndex, { duration_max_seconds })} />
                                  </>
                                ) : (
                                  <>
                                    <NumberField label={l(`حداقل تکرار ${labelSuffix}`, `Minimum reps ${labelSuffix}`)} value={exercise.reps_min ?? 8} onChange={(reps_min) => updateExercise(dayIndex, exerciseIndex, { reps_min })} />
                                    <NumberField label={l(`حداکثر تکرار ${labelSuffix}`, `Maximum reps ${labelSuffix}`)} value={exercise.reps_max ?? 12} onChange={(reps_max) => updateExercise(dayIndex, exerciseIndex, { reps_max })} />
                                    <NumberField label={`RIR ${labelSuffix}`} value={exercise.rir ?? 2} min={0} max={5} onChange={(rir) => updateExercise(dayIndex, exerciseIndex, { rir })} />
                                  </>
                                )}
                                <NumberField label={l(`استراحت ${labelSuffix}`, `Rest ${labelSuffix}`)} value={exercise.rest_seconds} step={15} onChange={(rest_seconds) => updateExercise(dayIndex, exerciseIndex, { rest_seconds })} />
                              </div>
                              <label>
                                {l("یادداشت فارسی حرکت", "Persian exercise note")}
                                <textarea value={exercise.notes_fa ?? ""} onChange={(event) => updateExercise(dayIndex, exerciseIndex, { notes_fa: event.target.value || null })} />
                              </label>
                              <label>
                                {l("یادداشت انگلیسی حرکت", "English exercise note")}
                                <textarea dir="ltr" value={exercise.notes_en ?? ""} onChange={(event) => updateExercise(dayIndex, exerciseIndex, { notes_en: event.target.value || null })} />
                              </label>
                            </fieldset>
                          </ReviewDisclosure>
                        );
                      })}
                      {!readOnly && (
                        <button
                          className="coach-review-add-exercise"
                          type="button"
                          disabled={busy || day.exercises.length >= 10}
                          onClick={() => addExercise(dayIndex)}
                        >{l(`افزودن حرکت به روز ${faNumber(day.day_number)}`, `Add exercise to day ${day.day_number}`)}</button>
                      )}
                    </ReviewDisclosure>
                  ))}
                </div>

                <label className="coach-review-note">
                  {l("یادداشت مربی برای کاربر", "Coach note for the member")}
                  <textarea disabled={busy || readOnly} value={coachNote} onChange={(event) => setCoachNote(event.target.value)} maxLength={2000} />
                </label>

                {!readOnly && (
                  <footer className="coach-review-actions">
                    <button type="button" disabled={busy} onClick={() => void saveDraft()}>{l("ذخیره پیش‌نویس", "Save draft")}</button>
                    <button className="is-reject" type="button" disabled={busy || !coachNote.trim()} onClick={() => void reject()}>{l("برگشت برای اصلاح", "Return for correction")}</button>
                    <button className="is-primary" type="button" disabled={busy} onClick={() => void approve()}>{l("ارسال برای تأیید کاربر", "Send for member approval")}</button>
                  </footer>
                )}
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

function TemplateSelectionAudit({
  selection,
  fa,
}: {
  selection: CoachTemplateSelection;
  fa: boolean;
}) {
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
      <ReviewDisclosure
        className="coach-template-disclosure"
        section="coach-rationale"
        summary={fa ? selection.explanation_fa : selection.explanation_en}
        title={fa ? "علت انتخاب برنامه" : "Why this program was selected"}
      >
        <details>
          <summary>{fa ? "جزئیات امتیازدهی" : "Scoring details"}</summary>
          <div className="coach-template-selection-details">
            <div className="coach-template-slug">
              <span>{fa ? "قالب منتخب" : "Selected template"}</span>
              <code dir="ltr">{selection.selected_template}</code>
            </div>
            <dl>
              {scores.map(([label, value]) => (
                <div key={label} className={label === (fa ? "مجموع" : "Total") ? "is-total" : undefined}>
                  <dt>{label}</dt>
                  <dd>{number.format(value)}</dd>
                </div>
              ))}
            </dl>
          </div>
        </details>
      </ReviewDisclosure>
    </section>
  );
}

function NumberField({ label, value, onChange, step = 1, min = 1, max }: { label: string; value: number; onChange: (value: number) => void; step?: number; min?: number; max?: number }) {
  return <label>{label}<input aria-label={label} type="number" min={min} max={max} step={step} value={value} onChange={(event) => onChange(Number(event.target.value))} /></label>;
}

function queueTitle(view: WorkoutReviewQueueView, fa: boolean) {
  if (view === "pending") return fa ? "در انتظار بررسی" : "Waiting";
  if (view === "mine") return fa ? "در حال بررسی من" : "My reviews";
  return fa ? "تأییدشده" : "Approved";
}

function sentAtLabel(value: string, fa: boolean): string {
  return fa
    ? `ارسال‌شده: ${formatTehranDateTime(value)}`
    : `Sent: ${formatTehranDateTimeForLocale(value, "en-US")}`;
}

function approvedAtLabel(value: string, fa: boolean): string {
  return fa
    ? `تاریخ تأیید: ${formatTehranDateTime(value)}`
    : `Approved: ${formatTehranDateTimeForLocale(value, "en-US")}`;
}

function statusTitle(status: WorkoutReviewQueueItem["status"], fa: boolean) {
  const labels = {
    pending: fa ? "در انتظار" : "Waiting",
    claimed: fa ? "در حال بررسی" : "In review",
    awaiting_member_acceptance: fa ? "در انتظار تایید کاربر" : "Awaiting member approval",
    member_changes_requested: fa ? "درخواست اصلاح کاربر" : "Member requested changes",
    approved: fa ? "تأییدشده" : "Approved",
    rejected: fa ? "برگشت‌داده‌شده" : "Returned",
    superseded: fa ? "بایگانی‌شده" : "Archived",
  };
  return labels[status];
}

function humanize(value: string | null, fa: boolean) {
  if (!value) return fa ? "ثبت نشده" : "Not provided";
  const labels: Record<string, [string, string]> = {
    build_muscle: ["عضله‌سازی", "Build muscle"],
    lose_weight: ["کاهش وزن", "Lose weight"],
    beginner: ["مبتدی", "Beginner"],
    intermediate: ["متوسط", "Intermediate"],
    advanced: ["پیشرفته", "Advanced"],
  };
  const translated = labels[value];
  return translated ? translated[fa ? 0 : 1] : value.replaceAll("_", " ");
}

function faNumber(value: number) {
  return value.toLocaleString("fa-IR", { useGrouping: false });
}

function newExerciseDraft(
  orderIndex: number,
  option: WorkoutReviewDetail["exercise_options"][number] | undefined,
): WorkoutReviewExerciseDraft {
  const duration = option?.prescription_mode === "duration";
  return {
    order_index: orderIndex,
    exercise_id: option?.id ?? "",
    sets: 3,
    prescription_mode: duration ? "duration" : "reps",
    reps_min: duration ? null : 8,
    reps_max: duration ? null : 12,
    duration_min_seconds: duration ? option?.duration_min_seconds ?? null : null,
    duration_max_seconds: duration ? option?.duration_max_seconds ?? null : null,
    rir: duration ? null : 2,
    rest_seconds: 90,
    notes_en: null,
    notes_fa: null,
  };
}

function renumberExercises(exercises: WorkoutReviewExerciseDraft[]) {
  return exercises.map((exercise, index) => ({ ...exercise, order_index: index + 1 }));
}

function renumberDays(days: WorkoutReviewDayDraft[]) {
  return days.map((day, index) => ({
    ...day,
    day_number: index + 1,
    exercises: renumberExercises(day.exercises),
  }));
}
