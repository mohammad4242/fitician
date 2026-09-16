import { useCallback, useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate, useSearchParams } from "react-router-dom";

import { formatTehranTimeForLocale } from "@fitician/core";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { AuthenticatedHeader } from "../../shared/AuthenticatedHeader";
import { SpecialistWorkbenchShell } from "../../shared/specialistWorkbench";
import type { SpecialistSection } from "../../shared/specialistWorkbench";
import { CoachDashboard } from "./CoachDashboard";
import { CoachReviewCase } from "./CoachReviewCase";
import { CoachReviewQueue } from "./CoachReviewQueue";
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
  WorkoutReviewDayDraft,
  WorkoutReviewDetail,
  WorkoutReviewExerciseDraft,
  WorkoutReviewQueueItem,
  WorkoutReviewQueueView,
} from "./types";
import "./coachWorkoutReview.css";

const queueViews: WorkoutReviewQueueView[] = ["pending", "mine", "approved"];
const emptyQueues: Record<WorkoutReviewQueueView, WorkoutReviewQueueItem[]> = {
  approved: [],
  mine: [],
  pending: [],
};
const emptyLoading: Record<WorkoutReviewQueueView, boolean> = {
  approved: true,
  mine: true,
  pending: true,
};

export function CoachWorkoutReviewPage() {
  const { i18n } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const fa = i18n.resolvedLanguage !== "en";
  const l = useCallback((faText: string, enText: string) => (fa ? faText : enText), [fa]);
  const activeSection = readSection(searchParams.get("section"));
  const [queues, setQueues] = useState<Record<WorkoutReviewQueueView, WorkoutReviewQueueItem[]>>(emptyQueues);
  const [loadingQueues, setLoadingQueues] = useState<Record<WorkoutReviewQueueView, boolean>>(emptyLoading);
  const [queueErrors, setQueueErrors] = useState<Partial<Record<WorkoutReviewQueueView, unknown>>>({});
  const [selected, setSelected] = useState<WorkoutReviewDetail | null>(null);
  const [draft, setDraft] = useState<WorkoutReviewDayDraft[]>([]);
  const [coachNote, setCoachNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<unknown>(null);
  const allQueuesLoading = queueViews.some((view) => loadingQueues[view]);
  const currentQueueView = queueViewForSection(activeSection);
  const currentQueue = queues[currentQueueView];
  const currentQueueLoading = loadingQueues[currentQueueView];
  const firstQueueError = queueViews.map((view) => queueErrors[view]).find((cause) => cause !== undefined);
  const visibleApiError = apiError ?? firstQueueError;
  const leaseLabel = useMemo(() => {
    if (!selected?.lease_expires_at) return l("بدون قفل فعال", "No active lease");
    return formatTehranTimeForLocale(selected.lease_expires_at, fa ? "fa-IR" : "en");
  }, [fa, l, selected?.lease_expires_at]);

  const loadQueue = useCallback(async (nextView: WorkoutReviewQueueView) => {
    setLoadingQueues((current) => ({ ...current, [nextView]: true }));
    try {
      const items = await listWorkoutReviews(nextView);
      setQueues((current) => ({ ...current, [nextView]: items }));
      setQueueErrors((current) => ({ ...current, [nextView]: undefined }));
      setApiError(null);
    } catch (cause) {
      setQueueErrors((current) => ({ ...current, [nextView]: cause }));
      setApiError(cause);
    } finally {
      setLoadingQueues((current) => ({ ...current, [nextView]: false }));
    }
  }, []);

  const loadAllQueues = useCallback(async () => {
    const results = await Promise.all(queueViews.map(async (view) => {
      setLoadingQueues((current) => ({ ...current, [view]: true }));
      try {
        return { items: await listWorkoutReviews(view), view } as const;
      } catch (cause) {
        return { cause, view } as const;
      }
    }));
    let firstError: unknown;
    const nextQueues = { ...emptyQueues };
    const nextErrors: Partial<Record<WorkoutReviewQueueView, unknown>> = {};
    for (const result of results) {
      if ("items" in result) nextQueues[result.view] = result.items ?? [];
      else {
        nextErrors[result.view] = result.cause;
        firstError ??= result.cause;
      }
    }
    setQueues(nextQueues);
    setQueueErrors(nextErrors);
    setApiError(firstError ?? null);
    setLoadingQueues({ approved: false, mine: false, pending: false });
  }, []);

  useEffect(() => {
    void loadAllQueues();
  }, [loadAllQueues]);

  useEffect(() => {
    if (selected?.status !== "claimed") return;
    const timer = window.setInterval(() => {
      void renewWorkoutReview(selected.id)
        .then((updated) => setSelected(updated))
        .catch((cause) => setApiError(cause));
    }, 8 * 60 * 1000);
    return () => window.clearInterval(timer);
  }, [selected?.id, selected?.status]);

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

  function changeSection(section: SpecialistSection, clearSelected = true) {
    setSearchParams((current) => {
      const next = new URLSearchParams(current);
      next.set("section", section);
      return next;
    }, { replace: true });
    if (clearSelected) clearSelectedReview();
  }

  async function openReview(item: WorkoutReviewQueueItem, sourceView: WorkoutReviewQueueView = currentQueueView) {
    setBusy(true);
    setError(null);
    setApiError(null);
    try {
      const nextView = item.status === "pending" ? "mine" : sourceView;
      const detail = item.status === "pending"
        ? await claimWorkoutReview(item.id)
        : await getWorkoutReview(item.id);
      openDetail(detail);
      if (nextView !== currentQueueView) {
        const nextSection: SpecialistSection = nextView === "approved" ? "history" : nextView === "mine" ? "mine" : "queue";
        changeSection(nextSection, false);
      }
      await loadQueue(nextView);
    } catch (cause) {
      await loadQueue(sourceView);
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  function updateExercise(dayIndex: number, exerciseIndex: number, patch: Partial<WorkoutReviewExerciseDraft>) {
    setDraft((current) => current.map((day, index) => index !== dayIndex ? day : {
      ...day,
      exercises: day.exercises.map((exercise, itemIndex) => itemIndex === exerciseIndex ? { ...exercise, ...patch } : exercise),
    }));
  }

  function updateDay(dayIndex: number, patch: Partial<WorkoutReviewDayDraft>) {
    setDraft((current) => current.map((day, index) => index === dayIndex ? { ...day, ...patch } : day));
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
    setError(null);
    setDraft((current) => [...current, {
      day_number: current.length + 1,
      title_en: null,
      title_fa: null,
      exercises: [newExerciseDraft(1, selected.exercise_options[0])],
    }]);
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
    setDraft((current) => current.map((day, index) => index !== dayIndex ? day : {
      ...day,
      exercises: [...day.exercises, newExerciseDraft(day.exercises.length + 1, selected.exercise_options[0])],
    }));
  }

  function removeExercise(dayIndex: number, exerciseIndex: number) {
    const day = draft[dayIndex];
    if (!day || day.exercises.length <= 1) {
      setError(l("برای حذف آخرین حرکت، روز را حذف کن.", "Remove the day to remove its last exercise."));
      return;
    }
    setError(null);
    setDraft((current) => current.map((item, index) => index !== dayIndex ? item : {
      ...item,
      exercises: renumberExercises(item.exercises.filter((_, itemIndex) => itemIndex !== exerciseIndex)),
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
      clearSelectedReview();
      changeSection("mine", false);
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
      clearSelectedReview();
      changeSection("mine", false);
      await loadQueue("mine");
    } catch (cause) {
      setApiError(cause);
    } finally {
      setBusy(false);
    }
  }

  const counts = {
    dashboard: queues.pending.length + queues.mine.length + queues.approved.length,
    history: queues.approved.length,
    mine: queues.mine.length,
    queue: queues.pending.length,
  };

  return (
    <div className="coach-review-shell">
      <AuthenticatedHeader />
      <SpecialistWorkbenchShell
        counts={counts}
        description={l("پرونده‌ها را سریع مرور کن، نسخه را دقیق اصلاح کن و تصمیم نهایی را ثبت کن.", "Review cases quickly, refine the plan precisely, and record the final decision.")}
        error={(
          <>
            <AppErrorNotice audience="coach" context="specialist_review" error={visibleApiError} locale={fa ? "fa" : "en"} />
            {error ? <p className="coach-review-error" role="alert">{error}</p> : null}
          </>
        )}
        fa={fa}
        headerAction={(
          <div className="coach-review-hero-actions">
            <button className="coach-review-back" onClick={() => navigate(-1)} type="button">
              {l("بازگشت", "Back")}
            </button>
            <aside aria-label={l("زمان قفل بازبینی", "Review lease time")} className="coach-review-lease">
              <small>{l("قفل بازبینی تا", "Review lease until")}</small>
              <strong>{leaseLabel}</strong>
            </aside>
          </div>
        )}
        onSectionChange={(section) => changeSection(section)}
        role="coach"
        title={l("بازبینی برنامه‌های تمرینی", "Workout plan reviews")}
        activeSection={activeSection}
      >
        {selected ? (
          <CoachReviewCase
            busy={busy}
            coachNote={coachNote}
            draft={draft}
            error={error}
            fa={fa}
            key={selected.id}
            onAddDay={addDay}
            onAddExercise={addExercise}
            onApprove={() => void approve()}
            onBack={clearSelectedReview}
            onCoachNoteChange={setCoachNote}
            onMoveDay={moveDay}
            onMoveExercise={moveExercise}
            onReject={() => void reject()}
            onRemoveDay={removeDay}
            onRemoveExercise={removeExercise}
            onSaveDraft={() => void saveDraft()}
            onUpdateDay={updateDay}
            onUpdateExercise={updateExercise}
            selected={selected}
          />
        ) : activeSection === "dashboard" ? (
          allQueuesLoading ? <p className="specialist-workbench-loading" role="status">{l("در حال آماده‌سازی داشبورد…", "Preparing dashboard…")}</p> : (
            <CoachDashboard
              approved={queues.approved}
              fa={fa}
              mine={queues.mine}
              onOpenCase={(item, sourceView) => void openReview(item, sourceView)}
              onSectionChange={changeSection}
              pending={queues.pending}
            />
          )
        ) : (
          <CoachReviewQueue
            busy={busy}
            fa={fa}
            items={currentQueue}
            loading={currentQueueLoading}
            onOpenReview={(item) => void openReview(item, currentQueueView)}
            view={currentQueueView}
          />
        )}
      </SpecialistWorkbenchShell>
    </div>
  );
}

function readSection(value: string | null): SpecialistSection {
  return value === "queue" || value === "mine" || value === "history" ? value : "dashboard";
}

function queueViewForSection(section: SpecialistSection): WorkoutReviewQueueView {
  if (section === "mine") return "mine";
  if (section === "history") return "approved";
  return "pending";
}

function newExerciseDraft(orderIndex: number, option: WorkoutReviewDetail["exercise_options"][number] | undefined): WorkoutReviewExerciseDraft {
  const duration = option?.prescription_mode === "duration";
  return {
    duration_max_seconds: duration ? option?.duration_max_seconds ?? null : null,
    duration_min_seconds: duration ? option?.duration_min_seconds ?? null : null,
    exercise_id: option?.id ?? "",
    notes_en: null,
    notes_fa: null,
    order_index: orderIndex,
    prescription_mode: duration ? "duration" : "reps",
    reps_max: duration ? null : 12,
    reps_min: duration ? null : 8,
    rest_seconds: 90,
    rir: duration ? null : 2,
    sets: 3,
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
