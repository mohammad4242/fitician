import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { formatIsoDate, formatPersianDateWithWeekday, formatTehranDateTimeForLocale } from "@fitician/core";
import { localIsoDate, resolvedIanaTimeZone } from "@fitician/core/local-date";

import { ApiError } from "../../shared/apiClient";
import { AppIcon, type IconName } from "../../shared/AppIcon";
import { PersianDatePicker } from "../../shared/PersianDatePicker";
import { useEntitlements } from "../entitlements/EntitlementContext";
import { getProfile, updateProfile } from "../profile/api";
import type { WorkoutGenerationMethod } from "../profile/types";
import { ExerciseMedia } from "../exercises/ExerciseMedia";
import { getProgramTimelineToday } from "../programTimeline/api";
import type { ProgramTimelineToday, TimelineWorkoutSession, WorkoutTimelineState } from "../programTimeline/types";
import {
  completeWorkoutSession,
  downloadWorkoutPlanPdf,
  deleteWorkoutPlan,
  generateWorkoutPlan,
  getActiveWorkoutPlan,
  getCurrentWorkoutCycle,
  getWorkoutPlan,
  getWorkoutPlanHistory,
  recordExerciseReplacement,
  rescheduleWorkoutSession,
  skipWorkoutSession,
  startWorkoutCycle,
} from "./api";
import { WeeklyCheckInCard } from "./WeeklyCheckInCard";
import { EndCycleFeedbackCard } from "./EndCycleFeedbackCard";
import { formatPrescriptionTarget } from "./prescriptionFormatter";
import type {
  WorkoutExerciseReplacementReason,
  WorkoutExerciseReplacementScope,
  WorkoutPlan,
  WorkoutPlanExercise,
  WorkoutPlanVersionSummary,
} from "./types";
import "./workoutPlan.css";

type PlanState = "loading" | "empty" | "ready" | "error";
type WorkoutPlanSummaryStatus = "active" | "pending" | "inactive";
type GenerationError =
  | "cooldown"
  | "entitlement"
  | "failed"
  | "bodyweight_level"
  | "bodyweight_days"
  | "bodyweight_pull_up_bar"
  | "bodyweight_exercise";

type DeleteVersionError = { versionId: string; message: string };
type TimelineAction = "start" | "complete" | "skip" | "reschedule";
type VersionDetailErrors = Record<string, string>;

type WorkoutDaysPresentation = {
  focusedWorkoutDayId?: string | null;
  nextWorkoutDayId?: string | null;
  state?: WorkoutTimelineState;
};

const bodyweightGenerationErrors: Record<string, GenerationError> = {
  BODYWEIGHT_ONLY_LEVEL_NOT_SUPPORTED: "bodyweight_level",
  BODYWEIGHT_TEMPLATE_DAYS_NOT_SUPPORTED: "bodyweight_days",
  BODYWEIGHT_PULL_UP_BAR_REQUIRED: "bodyweight_pull_up_bar",
  BODYWEIGHT_TEMPLATE_EXERCISE_UNAVAILABLE: "bodyweight_exercise",
};

const workoutPlanStatusIcons: Record<WorkoutPlanSummaryStatus, IconName> = {
  active: "zap",
  pending: "clock",
  inactive: "lock",
};

const workoutPlanStatusLabels: Record<WorkoutPlanSummaryStatus, string> = {
  active: "workoutPlan.active",
  pending: "workoutPlan.pendingCoach",
  inactive: "workoutPlan.inactive",
};

function getWorkoutPlanSummaryStatus(plan: WorkoutPlan, historical: boolean): WorkoutPlanSummaryStatus {
  if (historical) return "inactive";
  if (plan.status === "pending_review" || plan.coach_review?.state === "pending_coach_review") return "pending";
  return plan.status === "active" ? "active" : "inactive";
}

function generationErrorMessageKey(error: GenerationError): string {
  if (error === "entitlement") return "entitlements.lockedAction";
  if (error === "cooldown") return "workoutPlan.generateCooldown";
  if (error === "bodyweight_level") return "workoutPlan.bodyweightLevelUnsupported";
  if (error === "bodyweight_days") return "workoutPlan.bodyweightDaysUnsupported";
  if (error === "bodyweight_pull_up_bar") return "workoutPlan.bodyweightPullUpBarRequired";
  if (error === "bodyweight_exercise") return "workoutPlan.bodyweightExerciseUnavailable";
  return "workoutPlan.generateError";
}

function isDeletableVersion(version: WorkoutPlanVersionSummary): boolean {
  return version.status === "superseded" || version.status === "failed";
}

async function loadMemberPlans() {
  const [activePlan, versions] = await Promise.all([
    getActiveWorkoutPlan(),
    getWorkoutPlanHistory().catch(() => [] as WorkoutPlanVersionSummary[]),
  ]);
  const pendingVersion = versions.find((version) => version.status === "pending_review");
  const pendingPlan = pendingVersion === undefined
    ? null
    : await getWorkoutPlan(pendingVersion.id).catch(() => null);
  return { activePlan, versions, pendingPlan };
}

export function WorkoutPlanPage({ planDurationWeeks }: { planDurationWeeks: number }) {
  const { i18n, t } = useTranslation();
  const [activePlan, setActivePlan] = useState<WorkoutPlan | null>(null);
  const [pendingPlan, setPendingPlan] = useState<WorkoutPlan | null>(null);
  const [selectedHistoricalPlan, setSelectedHistoricalPlan] = useState<WorkoutPlan | null>(null);
  const [history, setHistory] = useState<WorkoutPlanVersionSummary[]>([]);
  const [selectingVersionId, setSelectingVersionId] = useState<string | null>(null);
  const [expandedVersionId, setExpandedVersionId] = useState<string | null>(null);
  const [versionDetails, setVersionDetails] = useState<Record<string, WorkoutPlan>>({});
  const [loadingVersionId, setLoadingVersionId] = useState<string | null>(null);
  const [versionDetailErrors, setVersionDetailErrors] = useState<VersionDetailErrors>({});
  const [deletingVersionId, setDeletingVersionId] = useState<string | null>(null);
  const [deleteVersionError, setDeleteVersionError] = useState<DeleteVersionError | null>(null);
  const [deleteDialogVersion, setDeleteDialogVersion] = useState<WorkoutPlanVersionSummary | null>(null);
  const [state, setState] = useState<PlanState>("loading");
  const [generating, setGenerating] = useState(false);
  const [reused, setReused] = useState(false);
  const [generationError, setGenerationError] = useState<GenerationError | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [generationMethod, setGenerationMethod] = useState<WorkoutGenerationMethod>("fitician_coach");
  const [savingGenerationMethod, setSavingGenerationMethod] = useState(false);
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [pdfError, setPdfError] = useState(false);
  const [timeline, setTimeline] = useState<ProgramTimelineToday | null>(null);
  const [startDate, setStartDate] = useState(() => localIsoDate());
  const [timelineAction, setTimelineAction] = useState<TimelineAction | null>(null);
  const [timelineActionError, setTimelineActionError] = useState(false);
  const [deviceTimezone] = useState(() => resolvedIanaTimeZone());
  const { loading: entitlementsLoading, hasEntitlement } = useEntitlements();
  const canGenerate = hasEntitlement("training.plan.generate");
  const isEnglish = i18n.resolvedLanguage === "en";
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const pendingVersionId = history.find((version) => version.status === "pending_review")?.id ?? null;
  const loadedCurrentPlan = pendingVersionId === null
    ? activePlan
    : pendingPlan?.id === pendingVersionId
      ? pendingPlan
      : null;
  const currentPlan = loadedCurrentPlan;
  const displayedPlan = selectedHistoricalPlan ?? currentPlan;
  const isViewingHistorical = selectedHistoricalPlan !== null;
  const displayedPlanDuration = displayedPlan?.plan_duration_weeks ?? planDurationWeeks;
  const hasPendingReview = pendingVersionId !== null;
  const memberHistory = history.filter(
    (version) => version.status !== "pending_review" && version.id !== currentPlan?.id,
  );
  const liveTimeline = !isViewingHistorical
    && currentPlan?.status === "active"
    && timeline?.workout.workout_plan_id === currentPlan.id
    ? timeline
    : null;
  const liveWorkout = liveTimeline?.workout ?? null;
  const focusedWorkoutDayId = liveWorkout?.state === "overdue"
    ? liveWorkout.overdue_session?.workout_day_id
    : liveWorkout?.state === "workout_today" || liveWorkout?.state === "completed_today"
      ? liveWorkout.today_session?.workout_day_id
      : null;
  const nextWorkoutDayId = liveWorkout?.next_session?.workout_day_id ?? null;

  useEffect(() => {
    let active = true;
    setState("loading");
    void loadMemberPlans()
      .then(({ activePlan: loadedActivePlan, versions, pendingPlan: loadedPendingPlan }) => {
        if (!active) return;
        setActivePlan(loadedActivePlan);
        setPendingPlan(loadedPendingPlan);
        setHistory(versions);
        setState(loadedActivePlan === null && loadedPendingPlan === null ? "empty" : "ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => {
      active = false;
    };
  }, [loadAttempt]);

  useEffect(() => {
    void getProfile().then((profile) => {
      if (profile !== null) setGenerationMethod(profile.workout_generation_method ?? "fitician_coach");
    }).catch(() => undefined);
  }, []);

  useEffect(() => {
    let active = true;
    void getProgramTimelineToday(deviceTimezone)
      .then((loadedTimeline) => {
        if (!active || loadedTimeline === undefined) return;
        setTimeline(loadedTimeline);
        setStartDate(loadedTimeline.local_date);
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [deviceTimezone]);

  async function refreshTimeline() {
    const loadedTimeline = await getProgramTimelineToday(deviceTimezone);
    if (loadedTimeline !== undefined) setTimeline(loadedTimeline);
  }

  function startProgram() {
    if (currentPlan === null || currentPlan.status !== "active" || timelineAction !== null) return;
    setTimelineAction("start");
    setTimelineActionError(false);
    void startWorkoutCycle({
      workout_plan_id: currentPlan.id,
      start_date: startDate,
      timezone: deviceTimezone,
    })
      .then(async () => {
        await refreshTimeline();
        await getCurrentWorkoutCycle().catch(() => null);
      })
      .catch(() => setTimelineActionError(true))
      .finally(() => setTimelineAction(null));
  }

  function runSessionAction(action: Exclude<TimelineAction, "start">, request: () => Promise<unknown>) {
    if (timelineAction !== null) return;
    setTimelineAction(action);
    setTimelineActionError(false);
    void request()
      .then(() => refreshTimeline().catch(() => undefined))
      .catch(() => setTimelineActionError(true))
      .finally(() => setTimelineAction(null));
  }

  function completeSession(sessionId: string) {
    runSessionAction("complete", () => completeWorkoutSession(sessionId));
  }

  function skipSession(sessionId: string) {
    runSessionAction("skip", () => skipWorkoutSession(sessionId));
  }

  function rescheduleSession(sessionId: string, scheduledDate: string) {
    runSessionAction("reschedule", () => rescheduleWorkoutSession(sessionId, scheduledDate));
  }

  function changeGenerationMethod(method: WorkoutGenerationMethod) {
    const previous = generationMethod;
    setGenerationMethod(method);
    setSavingGenerationMethod(true);
    void updateProfile({ workout_generation_method: method })
      .catch(() => setGenerationMethod(previous))
      .finally(() => setSavingGenerationMethod(false));
  }

  function generate() {
    if (entitlementsLoading || !canGenerate || generating) return;
    setGenerating(true);
    setReused(false);
    setGenerationError(null);
    void generateWorkoutPlan()
      .then(async (result) => {
        setSelectedHistoricalPlan(null);
        setActivePlan(result.plan.status === "active" ? result.plan : null);
        setPendingPlan(result.plan.status === "pending_review" ? result.plan : null);
        setState("ready");
        setReused(result.reused);
        try {
          const {
            activePlan: loadedActivePlan,
            versions,
            pendingPlan: loadedPendingPlan,
          } = await loadMemberPlans();
          setActivePlan(loadedActivePlan);
          setPendingPlan(loadedPendingPlan);
          setHistory(versions);
          setState(loadedActivePlan === null && loadedPendingPlan === null ? "empty" : "ready");
        } catch {
          // The successful generation response is already a valid foreground plan.
        }
        await refreshTimeline().catch(() => undefined);
      })
      .catch((error: unknown) => {
        const errorKind = error instanceof ApiError && error.status === 429
          ? "cooldown"
          : error instanceof ApiError && error.status === 403
            ? "entitlement"
          : error instanceof ApiError && error.code !== null
            ? bodyweightGenerationErrors[error.code] ?? "failed"
            : "failed";
        setState(currentPlan === null ? "empty" : "ready");
        setGenerationError(errorKind);
      })
      .finally(() => setGenerating(false));
  }

  function loadVersionDetail(versionId: string) {
    if (versionDetails[versionId] !== undefined || loadingVersionId === versionId) return;
    setVersionDetailErrors((current) => {
      const next = { ...current };
      delete next[versionId];
      return next;
    });
    setLoadingVersionId(versionId);
    void getWorkoutPlan(versionId)
      .then((loadedPlan) => setVersionDetails((current) => ({ ...current, [versionId]: loadedPlan })))
      .catch(() => setVersionDetailErrors((current) => ({
        ...current,
        [versionId]: l(
          "اطلاعات این نسخه دریافت نشد. دوباره تلاش کن.",
          "This version could not be loaded. Try again.",
        ),
      })))
      .finally(() => setLoadingVersionId(null));
  }

  function toggleVersion(versionId: string) {
    if (expandedVersionId === versionId) {
      setExpandedVersionId(null);
      return;
    }
    setExpandedVersionId(versionId);
    loadVersionDetail(versionId);
  }

  function selectVersion(version: WorkoutPlanVersionSummary) {
    if (version.id === currentPlan?.id) {
      setSelectedHistoricalPlan(null);
      return;
    }
    const cachedPlan = versionDetails[version.id];
    if (cachedPlan !== undefined) {
      setSelectedHistoricalPlan(cachedPlan);
      setGenerationError(null);
      return;
    }
    setSelectingVersionId(version.id);
    void getWorkoutPlan(version.id)
      .then((loadedPlan) => {
        setVersionDetails((current) => ({ ...current, [version.id]: loadedPlan }));
        setSelectedHistoricalPlan(loadedPlan);
        setGenerationError(null);
      })
      .catch(() => undefined)
      .finally(() => setSelectingVersionId(null));
  }

  function openDeleteDialog(version: WorkoutPlanVersionSummary) {
    if (!isDeletableVersion(version) || versionDetails[version.id] === undefined) return;
    setDeleteVersionError(null);
    setDeleteDialogVersion(version);
  }

  function deleteVersion(version: WorkoutPlanVersionSummary) {
    if (!isDeletableVersion(version) || deletingVersionId === version.id) return;

    const wasViewingDeletedVersion = selectedHistoricalPlan?.id === version.id;
    setDeletingVersionId(version.id);
    setDeleteVersionError(null);
    void deleteWorkoutPlan(version.id)
      .then(async () => {
        const {
          activePlan: loadedActivePlan,
          versions,
          pendingPlan: loadedPendingPlan,
        } = await loadMemberPlans();
        setActivePlan(loadedActivePlan);
        setPendingPlan(loadedPendingPlan);
        setHistory(versions);
        if (wasViewingDeletedVersion) setSelectedHistoricalPlan(null);
        setState(loadedActivePlan === null && loadedPendingPlan === null ? "empty" : "ready");
        setDeleteDialogVersion(null);
        setExpandedVersionId((current) => current === version.id ? null : current);
        setVersionDetails((current) => {
          const next = { ...current };
          delete next[version.id];
          return next;
        });
      })
      .catch(() => {
        setDeleteVersionError({
          versionId: version.id,
          message: l(
            "حذف نسخه قدیمی برنامه انجام نشد؛ دوباره تلاش کن.",
            "The old workout plan version could not be deleted. Please try again.",
          ),
        });
      })
      .finally(() => setDeletingVersionId(null));
  }

  function downloadPdf() {
    if (displayedPlan === null || downloadingPdf) return;
    const planId = displayedPlan.id;
    setDownloadingPdf(true);
    setPdfError(false);
    void downloadWorkoutPlanPdf(planId)
      .then((blob) => {
        const url = URL.createObjectURL(blob);
        try {
          const anchor = document.createElement("a");
          anchor.href = url;
          anchor.download = `fitician-workout-plan-${planId}.pdf`;
          document.body.append(anchor);
          anchor.click();
          anchor.remove();
        } finally {
          URL.revokeObjectURL(url);
        }
      })
      .catch(() => setPdfError(true))
      .finally(() => setDownloadingPdf(false));
  }

  return (
    <div className="workout-plan-shell fitician-page">
      <main className="workout-plan-main">
        <div className="workout-plan-controls">
          <section className="workout-generation-method" aria-labelledby="workout-generation-method-title">
            <h2 id="workout-generation-method-title">{t("workoutPlan.generationMethodTitle")}</h2>
            <div className="workout-generation-method__choices" role="group" aria-labelledby="workout-generation-method-title">
              <label>
                <input type="radio" name="workout-generation-method" checked={generationMethod === "fitician_coach"} disabled={savingGenerationMethod} onChange={() => changeGenerationMethod("fitician_coach")} />
                <span>{t("workoutPlan.fiticianCoach")}</span>
              </label>
              <label>
                <input type="radio" name="workout-generation-method" checked={generationMethod === "ai"} disabled={savingGenerationMethod} onChange={() => changeGenerationMethod("ai")} />
                <span>{t("workoutPlan.aiOption")}</span>
              </label>
            </div>
          </section>
        {state === "ready" && currentPlan !== null && !isViewingHistorical && (
            <GenerateButton
              generating={generating}
              onClick={generate}
              update
              disabled={entitlementsLoading || !canGenerate || generationError === "cooldown"}
            />
          )}
          {state === "ready" && currentPlan !== null && !isViewingHistorical && !entitlementsLoading && !canGenerate && (
            <AccessLockedNotice />
          )}
        </div>

        {displayedPlan !== null
          ? <WorkoutPlanOverview plan={displayedPlan} historical={isViewingHistorical} isEnglish={isEnglish} />
          : (
            <header className="workout-plan-hero">
              <div className="workout-plan-hero__content">
                <p className="eyebrow">{t("workoutPlan.eyebrow")}</p>
                <h1 className="fitician-display">{t("workoutPlan.title")}</h1>
                <p>{t("workoutPlan.intro")}</p>
              </div>
              <div className="workout-plan-duration" aria-label={t("workoutPlan.duration", { count: displayedPlanDuration })}>
                <strong>{displayedPlanDuration}</strong>
                <span>{t("workoutPlan.weeks")}</span>
              </div>
            </header>
          )}

        {state === "ready" && liveTimeline !== null && currentPlan !== null && (
          <WorkoutTimelineCard
            timeline={liveTimeline}
            isEnglish={isEnglish}
            startDate={startDate}
            action={timelineAction}
            actionError={timelineActionError}
            onStartDateChange={setStartDate}
            onStart={startProgram}
            onComplete={completeSession}
            onSkip={skipSession}
            onReschedule={rescheduleSession}
          />
        )}

        {state === "loading" && <StatusPanel role="status" message={t("workoutPlan.loading")} />}
        {state === "error" && currentPlan === null && (
          <StatusPanel
            role="alert"
            message={t("workoutPlan.loadError")}
            action={t("common.retry")}
            onAction={() => setLoadAttempt((attempt) => attempt + 1)}
          />
        )}
        {state === "empty" && (
          <>
            {generationError !== null && (
              <StatusPanel
                role="alert"
                message={t(generationErrorMessageKey(generationError))}
                action={generationError === "failed" ? t("common.retry") : undefined}
                onAction={generationError === "failed" ? generate : undefined}
              />
            )}
            {hasPendingReview ? (
              <StatusPanel role="status" message={t("workoutPlan.loading")} />
            ) : (
              <section className="workout-empty" aria-labelledby="workout-empty-title">
                <h2 id="workout-empty-title" className="fitician-display">{t("workoutPlan.emptyTitle")}</h2>
                <p>{t("workoutPlan.emptyBody")}</p>
                <GenerateButton
                  generating={generating}
                  onClick={generate}
                  disabled={entitlementsLoading || !canGenerate || generationError === "cooldown"}
                />
                {!entitlementsLoading && !canGenerate && <AccessLockedNotice />}
              </section>
            )}
          </>
        )}
        {state === "ready" && displayedPlan !== null && (
          <>
            <section className="workout-schedule" aria-labelledby="workout-schedule-title">
              <div className="workout-schedule__heading">
                <div>
                  <p className="eyebrow eyebrow--accent">{t("workoutPlan.weekly")}</p>
                  <h2 id="workout-schedule-title" className="fitician-display">{t("workoutPlan.scheduleTitle")}</h2>
                </div>
              </div>
              {generating && <p className="workout-generating" role="status">{t("workoutPlan.generating")}</p>}
              <WorkoutDays
                plan={displayedPlan}
                isEnglish={isEnglish}
                titleId="workout-schedule-title"
                interactive={!isViewingHistorical && displayedPlan.status === "active"}
                presentation={liveWorkout === null ? undefined : {
                  focusedWorkoutDayId,
                  nextWorkoutDayId,
                  state: liveWorkout.state,
                }}
              />
            </section>
            <div className="workout-plan-statuses">
              {reused && <p className="workout-reused" role="status">{t("workoutPlan.reused")}</p>}
              {displayedPlan.ai_coach_program_explanation_fa && (
                <aside className="workout-ai-coach" aria-label={t("workoutPlan.aiCoach")}>
                  <span className="workout-ai-coach__icon" aria-hidden="true">✦</span>
                  <div><p>{t("workoutPlan.aiCoach")}</p><strong>{displayedPlan.ai_coach_program_explanation_fa}</strong></div>
                </aside>
              )}
              {displayedPlan.is_stale && <p className="workout-stale" role="status">{t("workoutPlan.stale")}</p>}
              {displayedPlan.warnings?.includes("SESSION_DURATION_EXTENDED_TO_PRESERVE_CORE") && <p className="workout-body-analysis-warning" role="alert">{t("workoutPlan.corePreservationDurationWarning")}</p>}
              {displayedPlan.body_analysis_provenance?.provisional === true && <p className="workout-body-analysis-warning" role="alert">{t("workoutPlan.provisionalBodyAnalysisWarning")}</p>}
              {generationError && <StatusPanel role="alert" message={t(generationErrorMessageKey(generationError))} action={generationError === "failed" ? t("common.retry") : undefined} onAction={generationError === "failed" ? generate : undefined} />}
            </div>
            {!isViewingHistorical && displayedPlan.status === "active" && <WeeklyCheckInCard plan={displayedPlan} />}
          </>
        )}
        <section className="workout-tools" aria-labelledby="workout-future-title">
          <h2 id="workout-future-title">{t("workoutPlan.futureTitle")}</h2>
          <div
            className={`workout-quick-actions${displayedPlan !== null ? " workout-quick-actions--with-feedback" : ""}`}
            role="group"
            aria-labelledby="workout-future-title"
          >
            <button
              className="workout-quick-action"
              type="button"
              disabled={displayedPlan === null || downloadingPdf}
              aria-busy={downloadingPdf}
              aria-label={t("workoutPlan.pdf.title")}
              onClick={downloadPdf}
            >
              <AppIcon name="document" />
              <strong>{t("workoutPlan.pdf.title")}</strong>
              <small>{t(downloadingPdf ? "workoutPlan.pdf.loading" : "workoutPlan.pdf.body")}</small>
            </button>
            {state !== "loading" && displayedPlan !== null && (
              <EndCycleFeedbackCard
                planDurationWeeks={displayedPlan.plan_duration_weeks}
                awaitingCoachApproval={displayedPlan.status === "pending_review"}
              />
            )}
            <Link className="workout-quick-action" aria-label={t("workoutPlan.body.title")} to="/body-progress">
              <AppIcon name="progress" />
              <strong>{t("workoutPlan.body.title")}</strong>
            </Link>
          </div>
          {pdfError && <StatusPanel role="alert" message={t("workoutPlan.pdf.error")} />}
        </section>

        <details className="workout-secondary">
          <summary>{l("جزئیات و تنظیمات برنامه", "Plan details and settings")}</summary>
          <div className="workout-secondary__content">
            <FixedGuidance />
            {displayedPlan?.ai_coach_program_explanation_fa && (
              <aside className="workout-ai-coach" aria-label={t("workoutPlan.aiCoach")}>
                <span className="workout-ai-coach__icon" aria-hidden="true">✦</span>
                <div><p>{t("workoutPlan.aiCoach")}</p><strong>{displayedPlan.ai_coach_program_explanation_fa}</strong></div>
              </aside>
            )}
            {(memberHistory.length > 0 || isViewingHistorical) && (
              <section className="workout-version-history" aria-labelledby="workout-version-history-title">
                <div><p className="eyebrow eyebrow--accent">{l("نسخه‌های برنامه", "Plan versions")}</p><h2 id="workout-version-history-title">{l("تاریخچه برنامه", "Plan history")}</h2></div>
                {isViewingHistorical && <button type="button" onClick={() => setSelectedHistoricalPlan(null)}>{l("بازگشت به برنامه فعلی", "Return to current plan")}</button>}
                <div className="workout-version-history__list">
                  {memberHistory.map((version, index) => {
                    const label = version.coach_review.state === "coach_approved"
                      ? l("نسخه تأیید مربی", "Coach-approved version")
                      : version.coach_review.state === "coach_rejected"
                        ? l("نسخه برگشت‌داده‌شده برای اصلاح", "Returned for correction")
                        : l("نسخه اولیه", "Initial version");
                    const canDelete = isDeletableVersion(version);
                    const planNumber = new Intl.NumberFormat(isEnglish ? "en-US" : "fa-IR").format(index + 1);
                    const planNumberLabel = l(`برنامه شماره ${planNumber}`, `Plan ${planNumber}`);
                    const timestamp = formatMemberTimestamp(version.created_at, isEnglish);
                    const isExpanded = expandedVersionId === version.id;
                    const detailsId = `workout-version-details-${version.id}`;
                    const detail = versionDetails[version.id];
                    const detailError = versionDetailErrors[version.id];
                    return (
                      <article className={`workout-version-history__item${isExpanded ? " workout-version-history__item--expanded" : ""}`} key={version.id}>
                        <button
                          type="button"
                          className="workout-version-history__toggle"
                          aria-expanded={isExpanded}
                          aria-controls={detailsId}
                          aria-busy={loadingVersionId === version.id}
                          aria-label={`${planNumberLabel} — ${label} — ${timestamp}`}
                          onClick={() => toggleVersion(version.id)}
                        >
                          <span className="workout-version-history__number">{planNumberLabel}</span>
                          <strong>{timestamp}</strong>
                          <span className="workout-version-history__status">{version.is_active ? l("فعال", "Active") : l("آرشیو", "Archived")}</span>
                          <span className="workout-version-history__chevron" aria-hidden="true">{isExpanded ? "−" : "+"}</span>
                        </button>
                        {isExpanded && (
                          <div className="workout-version-history__details" id={detailsId}>
                            {loadingVersionId === version.id && <p className="workout-version-history__loading" role="status">{l("در حال دریافت اطلاعات برنامه…", "Loading plan overview…")}</p>}
                            {detailError !== undefined && (
                              <div className="workout-version-history__error">
                                <p role="alert">{detailError}</p>
                                <button type="button" onClick={() => loadVersionDetail(version.id)}>{l("تلاش دوباره", "Try again")}</button>
                              </div>
                            )}
                            {detail !== undefined && (
                              <>
                                <WorkoutPlanHistoryOverview plan={detail} isEnglish={isEnglish} />
                                <div className="workout-version-history__actions">
                                  <button
                                    type="button"
                                    className="workout-version-history__inspect"
                                    disabled={selectingVersionId !== null}
                                    onClick={() => selectVersion(version)}
                                  >
                                    {l("مشاهده نسخه کامل", "View full version")}
                                  </button>
                                  {canDelete && (
                                    <button
                                      type="button"
                                      className="workout-version-history__delete"
                                      aria-label={l("حذف نسخه قدیمی برنامه", "Delete old plan version")}
                                      disabled={deletingVersionId === version.id}
                                      aria-busy={deletingVersionId === version.id}
                                      onClick={() => openDeleteDialog(version)}
                                    >
                                      {l("حذف نسخه", "Delete version")}
                                    </button>
                                  )}
                                </div>
                              </>
                            )}
                          </div>
                        )}
                      </article>
                    );
                  })}
                </div>
              </section>
            )}
          </div>
        </details>

      </main>
      {deleteDialogVersion !== null && versionDetails[deleteDialogVersion.id] !== undefined && (
        <WorkoutPlanDeleteDialog
          plan={versionDetails[deleteDialogVersion.id]}
          isEnglish={isEnglish}
          deleting={deletingVersionId === deleteDialogVersion.id}
          error={deleteVersionError?.versionId === deleteDialogVersion.id ? deleteVersionError.message : null}
          onCancel={() => {
            if (deletingVersionId === null) setDeleteDialogVersion(null);
          }}
          onConfirm={() => deleteVersion(deleteDialogVersion)}
        />
      )}
    </div>
  );
}

function WorkoutPlanHistoryOverview({ plan, isEnglish }: { plan: WorkoutPlan; isEnglish: boolean }) {
  const number = new Intl.NumberFormat(isEnglish ? "en-US" : "fa-IR");
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const source = plan.generation_source === "ai"
    ? l("هوش مصنوعی", "AI")
    : l("مربی فیتیشن", "Fitician Coach");

  return (
    <div className="workout-version-overview">
      <dl className="workout-version-overview__meta">
        <div>
          <dt>{l("تاریخ ساخت", "Created")}</dt>
          <dd><time dateTime={plan.created_at}>{formatMemberTimestamp(plan.created_at, isEnglish)}</time></dd>
        </div>
        <div>
          <dt>{l("روش ساخت", "Created by")}</dt>
          <dd>{source}</dd>
        </div>
        <div>
          <dt>{l("مدت برنامه", "Duration")}</dt>
          <dd>{number.format(plan.plan_duration_weeks)} {l("هفته", "weeks")}</dd>
        </div>
        <div>
          <dt>{l("فرم کلی", "Format")}</dt>
          <dd>{l(`${number.format(plan.days.length)} روز تمرین`, `${number.format(plan.days.length)} training days`)}</dd>
        </div>
      </dl>
      <div className="workout-version-overview__days">
        <p>{l("روزهای برنامه", "Training days")}</p>
        <ul>
          {plan.days.map((day) => <li key={day.id}>{isEnglish ? day.title_en : day.title_fa}</li>)}
        </ul>
      </div>
    </div>
  );
}

function WorkoutPlanDeleteDialog({
  plan,
  isEnglish,
  deleting,
  error,
  onCancel,
  onConfirm,
}: {
  plan: WorkoutPlan;
  isEnglish: boolean;
  deleting: boolean;
  error: string | null;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const dialogTitle = l("حذف نسخه قدیمی برنامه", "Delete old workout plan version");

  return (
    <div className="workout-delete-dialog-backdrop">
      <section
        className="workout-delete-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="workout-delete-dialog-title"
      >
        <header className="workout-delete-dialog__header">
          <div>
            <p className="eyebrow eyebrow--accent">{l("عملیات حساس", "Sensitive action")}</p>
            <h2 id="workout-delete-dialog-title">{dialogTitle}</h2>
          </div>
          <button
            type="button"
            className="workout-delete-dialog__close"
            aria-label={l("بستن", "Close")}
            disabled={deleting}
            onClick={onCancel}
          >
            ×
          </button>
        </header>
        <p className="workout-delete-dialog__body">
          {l("این نسخه و اطلاعات کلی آن از تاریخچه برنامه‌ها حذف می‌شود و قابل بازگشت نیست.", "This version and its overview will be removed from your plan history and cannot be restored.")}
        </p>
        <WorkoutPlanHistoryOverview plan={plan} isEnglish={isEnglish} />
        {error !== null && (
          <StatusPanel role="alert" message={error} action={l("تلاش دوباره", "Retry")} onAction={onConfirm} />
        )}
        <footer className="workout-delete-dialog__actions">
          <button type="button" className="workout-delete-dialog__cancel" disabled={deleting} onClick={onCancel}>
            {l("انصراف", "Cancel")}
          </button>
          <button
            type="button"
            className="workout-delete-dialog__confirm"
            disabled={deleting}
            aria-busy={deleting}
            onClick={onConfirm}
          >
            {deleting ? l("در حال حذف…", "Deleting…") : l("حذف دائمی", "Delete permanently")}
          </button>
        </footer>
      </section>
    </div>
  );
}

function WorkoutPlanOverview({
  plan,
  historical,
  isEnglish,
}: {
  plan: WorkoutPlan;
  historical: boolean;
  isEnglish: boolean;
}) {
  const { t } = useTranslation();
  const number = new Intl.NumberFormat(isEnglish ? "en-US" : "fa-IR");
  const summaryStatus = getWorkoutPlanSummaryStatus(plan, historical);
  const durations = plan.days
    .map((day) => day.estimated_duration_minutes)
    .filter((duration): duration is number => duration !== null && duration !== undefined);
  const averageSession = durations.length === 0
    ? null
    : Math.round(durations.reduce((total, duration) => total + duration, 0) / durations.length);
  const l = (fa: string, en: string) => isEnglish ? en : fa;

  return (
    <section className="workout-plan-overview" data-testid={`workout-plan-overview-${plan.id}`}>
      <header className="workout-plan-hero">
        <div className="workout-plan-hero__content">
          <p className="eyebrow">{t("workoutPlan.eyebrow")}</p>
          <h1 className="fitician-display">{t("workoutPlan.title")}</h1>
          <p>{t("workoutPlan.intro")}</p>
        </div>
        <div className="workout-plan-duration" aria-label={t("workoutPlan.duration", { count: plan.plan_duration_weeks })}>
          <strong>{plan.plan_duration_weeks}</strong>
          <span>{t("workoutPlan.weeks")}</span>
        </div>
      </header>

      <section className="workout-plan-context" aria-label={t("workoutPlan.contextLabel")}>
        <span>
          <small>{t("workoutPlan.currentPlan")}</small>
          <strong className={`workout-plan-context__status workout-plan-context__status--${summaryStatus}`}>
            <AppIcon name={workoutPlanStatusIcons[summaryStatus]} className="workout-plan-context__status-icon" />
            {t(workoutPlanStatusLabels[summaryStatus])}
          </strong>
        </span>
        <span>
          <small>{t("workoutPlan.prePlan")}</small>
          <strong>
            {plan.generation_source === "ai"
              ? t("workoutPlan.aiSource")
              : plan.generation_source === "internal_engine"
                ? t("workoutPlan.internalEngineSource")
                : "—"}
          </strong>
        </span>
        <span>
          <small>{t("workoutPlan.trainingDays")}</small>
          <strong>{t("workoutPlan.daysCount", { count: number.format(plan.days.length) })}</strong>
        </span>
        <span>
          <small>{t("workoutPlan.sessionDuration")}</small>
          <strong>
            {averageSession === null
              ? "—"
              : t("workoutPlan.perSession", { count: number.format(averageSession) })}
          </strong>
        </span>
      </section>

      <CoachReviewBanner plan={plan} isEnglish={isEnglish} historical={historical} />
      {historical && <p className="workout-plan-readonly" role="note">{l("این نسخه فقط برای مشاهده است.", "This version is read-only.")}</p>}
    </section>
  );
}

function CoachReviewBanner({ plan, isEnglish, historical }: { plan: WorkoutPlan; isEnglish: boolean; historical: boolean }) {
  const review = plan.coach_review;
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  if (historical) {
    return <p className="workout-review-banner workout-review-banner--history" role="status">{l("در حال مشاهده نسخه قبلی", "Viewing a previous version")}</p>;
  }
  if (plan.status === "pending_review" || review?.state === "pending_coach_review") {
    return (
      <aside className="workout-review-banner workout-review-banner--pending" role="status">
        <span className="workout-review-indicator" aria-hidden="true" />
        <strong>{l("در انتظار تایید مربی", "Waiting for coach approval")}</strong>
      </aside>
    );
  }
  if (review?.state === "coach_approved") {
    const coach = review.coach_display_name ?? l("مربی فیتیشن", "Fitician coach");
    return (
      <aside className="workout-review-banner workout-review-banner--approved" role="status">
        <span className="workout-review-indicator" aria-hidden="true">✓</span>
        <div>
          <strong>{l(`تأییدشده توسط ${coach}`, `Approved by ${coach}`)}</strong>
          {review.approved_at && <time dateTime={review.approved_at}>{formatMemberTimestamp(review.approved_at, isEnglish)}</time>}
          {review.coach_note && <p>{review.coach_note}</p>}
        </div>
      </aside>
    );
  }
  if (review?.state === "coach_rejected") {
    return (
      <aside className="workout-review-banner workout-review-banner--pending" role="status">
        <span className="workout-review-indicator" aria-hidden="true">!</span>
        <div>
          <strong>{l("نیاز به اصلاح طبق نظر مربی", "Returned for coach corrections")}</strong>
          {review.coach_note && <p>{review.coach_note}</p>}
        </div>
      </aside>
    );
  }
  return (
    <aside className="workout-review-banner workout-review-banner--approved" role="status">
      <span className="workout-review-indicator" aria-hidden="true">✓</span>
      <strong>{l("برنامه آماده اجراست", "Ready to train")}</strong>
    </aside>
  );
}

function formatTimelineDate(value: string, isEnglish: boolean): string {
  return isEnglish ? formatIsoDate(value, "en-US") : formatPersianDateWithWeekday(value);
}

function formatMemberTimestamp(value: string, isEnglish: boolean): string {
  return formatTehranDateTimeForLocale(value, isEnglish ? "en-US" : "fa-IR");
}

function WorkoutTimelineCard({
  timeline,
  isEnglish,
  startDate,
  action,
  actionError,
  onStartDateChange,
  onStart,
  onComplete,
  onSkip,
  onReschedule,
}: {
  timeline: ProgramTimelineToday;
  isEnglish: boolean;
  startDate: string;
  action: TimelineAction | null;
  actionError: boolean;
  onStartDateChange: (value: string) => void;
  onStart: () => void;
  onComplete: (sessionId: string) => void;
  onSkip: (sessionId: string) => void;
  onReschedule: (sessionId: string, scheduledDate: string) => void;
}) {
  const { t } = useTranslation();
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const workout = timeline.workout;
  const focusSession = workout.state === "overdue"
    ? workout.overdue_session
    : workout.today_session;
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [rescheduleDate, setRescheduleDate] = useState(timeline.local_date);
  const nextSession = workout.next_session;
  const formatDate = (value: string) => formatTimelineDate(value, isEnglish);

  function sessionDescription(session: TimelineWorkoutSession): string {
    return t("workoutPlan.nextSessionDetails", {
      date: formatDate(session.scheduled_date),
      session: session.session_number,
      title: isEnglish ? session.title_en : session.title_fa,
    });
  }

  function renderNextSession() {
    if (nextSession === null || nextSession === undefined) return null;
    return (
      <p className="workout-timeline-card__next">
        <strong>{t("workoutPlan.nextSession")}</strong> {sessionDescription(nextSession)}
      </p>
    );
  }

  function renderSessionMeta(session: TimelineWorkoutSession) {
    return (
      <p className="workout-timeline-card__meta">
        {t("workoutPlan.sessionWeek", {
          session: session.session_number,
          week: session.week_number,
          total: workout.duration_weeks ?? "—",
        })}
        {" · "}
        {isEnglish ? session.title_en : session.title_fa}
      </p>
    );
  }

  return (
    <section className={"workout-timeline-card workout-timeline-card--" + workout.state} aria-live="polite">
      <div className="workout-timeline-card__heading">
        <div>
          <p className="eyebrow eyebrow--accent">{t("workoutPlan.programTimelineEyebrow")}</p>
          <h2 className="fitician-display">
            {workout.state === "ready_to_start" && t("workoutPlan.programReady")}
            {workout.state === "scheduled_start" && t("workoutPlan.programScheduled")}
            {workout.state === "workout_today" && t("workoutPlan.todayWorkout")}
            {workout.state === "rest_day" && t("workoutPlan.restDay")}
            {workout.state === "overdue" && t("workoutPlan.overdueSession")}
            {workout.state === "completed_today" && t("workoutPlan.sessionCompletedToday")}
            {workout.state === "legacy_cycle" && t("workoutPlan.legacyTrackingUnavailable")}
            {workout.state === "cycle_completed" && t("workoutPlan.cycleCompleted")}
          </h2>
        </div>
        {workout.current_week !== null && workout.current_week !== undefined && workout.duration_weeks !== null && workout.duration_weeks !== undefined && (
          <span className="workout-timeline-card__week">
            {t("workoutPlan.weekProgress", { current: workout.current_week, total: workout.duration_weeks })}
          </span>
        )}
      </div>

      {workout.state === "ready_to_start" && (
        <div className="workout-timeline-card__start">
          <PersianDatePicker
            ariaLabel={t("workoutPlan.startDate")}
            label={t("workoutPlan.startDate")}
            onChange={onStartDateChange}
            value={startDate}
          />
          <button className="workout-timeline-card__primary" type="button" disabled={action !== null || startDate === ""} onClick={onStart}>
            {action === "start" ? t("workoutPlan.starting") : t("workoutPlan.startProgram")}
          </button>
        </div>
      )}

      {workout.state === "scheduled_start" && workout.start_date !== null && workout.start_date !== undefined && (
        <p>{t("workoutPlan.programStartsOn", { date: formatDate(workout.start_date) })}</p>
      )}

      {workout.state === "workout_today" && focusSession !== null && focusSession !== undefined && (
        <>
          {renderSessionMeta(focusSession)}
          <button className="workout-timeline-card__primary" type="button" disabled={action !== null} onClick={() => onComplete(focusSession.id)}>
            {action === "complete" ? t("workoutPlan.savingSession") : t("workoutPlan.completeWorkout")}
          </button>
        </>
      )}

      {workout.state === "overdue" && focusSession !== null && focusSession !== undefined && (
        <>
          <p>{t("workoutPlan.originallyScheduled", { date: formatDate(focusSession.scheduled_date) })}</p>
          {renderSessionMeta(focusSession)}
          <div className="workout-timeline-card__actions">
            <button className="workout-timeline-card__primary" type="button" disabled={action !== null} onClick={() => onReschedule(focusSession.id, timeline.local_date)}>
              {action === "reschedule" ? t("workoutPlan.savingSession") : t("workoutPlan.doToday")}
            </button>
            <button type="button" disabled={action !== null} onClick={() => setRescheduleOpen((open) => !open)}>
              {t("workoutPlan.reschedule")}
            </button>
            <button type="button" disabled={action !== null} onClick={() => onSkip(focusSession.id)}>
              {action === "skip" ? t("workoutPlan.savingSession") : t("workoutPlan.skipSession")}
            </button>
          </div>
          {rescheduleOpen && (
            <div className="workout-timeline-card__reschedule">
              <PersianDatePicker
                ariaLabel={t("workoutPlan.rescheduleDate")}
                label={t("workoutPlan.rescheduleDate")}
                min={workout.start_date ?? undefined}
                onChange={setRescheduleDate}
                value={rescheduleDate}
              />
              <button className="workout-timeline-card__primary" type="button" disabled={action !== null || rescheduleDate === ""} onClick={() => onReschedule(focusSession.id, rescheduleDate)}>
                {t("workoutPlan.applyReschedule")}
              </button>
            </div>
          )}
        </>
      )}

      {workout.state === "rest_day" && <p>{l("امروز تمرین نداری؛ برای ریکاوری وقت بگذار.", "No workout is scheduled today; use the day to recover.")}</p>}
      {(workout.state === "rest_day" || workout.state === "completed_today" || workout.state === "overdue") && renderNextSession()}
      {workout.state === "legacy_cycle" && <p>{l("اطلاعات دوره و چک‌این هفتگی همچنان در دسترس است.", "Your cycle summary and weekly check-in are still available.")}</p>}
      {workout.state === "cycle_completed" && <p>{l("برای ادامه، برنامه بعدی‌ات را انتخاب یا آماده کن.", "Choose or prepare your next plan to continue.")}</p>}
      {actionError && <p className="workout-timeline-card__error" role="alert">{t("workoutPlan.sessionActionError")}</p>}
    </section>
  );
}

function WorkoutDays({ plan, isEnglish, titleId, interactive, presentation }: { plan: WorkoutPlan; isEnglish: boolean; titleId: string; interactive: boolean; presentation?: WorkoutDaysPresentation }) {
  const { t } = useTranslation();
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  return (
    <div className="workout-days" role="list" aria-labelledby={titleId}>
      {plan.days.map((day) => {
        const mainExercises = day.exercises.filter((item) => item.section !== "core");
        const coreExercises = day.exercises.filter((item) => item.section === "core");
        const leadExercise = mainExercises[0] ?? day.exercises[0];
        const isFocused = presentation?.focusedWorkoutDayId !== null
          && presentation?.focusedWorkoutDayId !== undefined
          && presentation.focusedWorkoutDayId === day.id;
        const isNext = !isFocused
          && presentation?.nextWorkoutDayId !== null
          && presentation?.nextWorkoutDayId !== undefined
          && presentation.nextWorkoutDayId === day.id;
        const focusLabel = isFocused && presentation?.state === "overdue"
          ? l("جلسه عقب‌افتاده", "Overdue session")
          : isFocused && presentation?.state === "completed_today"
            ? l("تکمیل‌شده امروز", "Completed today")
            : isFocused
              ? t("workoutPlan.todayWorkout")
              : isNext
                ? t("workoutPlan.nextSession")
                : null;
        const renderExercises = (exercises: WorkoutPlanExercise[]) => (
          <ol>
            {exercises.map((item, itemIndex) => {
              const groupIndices = item.superset_group
                ? exercises.flatMap((candidate, index) => (
                  candidate.superset_group === item.superset_group ? [index] : []
                ))
                : [];
              const isSuperset = groupIndices.length === 2
                && groupIndices[1] === groupIndices[0]! + 1;
              const isSupersetStart = isSuperset && itemIndex === groupIndices[0];
              return (
                <li className={`workout-exercise${isSuperset ? " workout-exercise--superset" : ""}`} key={item.order_index}>
                  <ExerciseMedia
                    path={item.exercise.media_path}
                    name={isEnglish ? item.exercise.name_en : item.exercise.name_fa}
                    mediaType={item.exercise.media_type}
                  />
                  <div className="workout-exercise__content">
                    <div className="workout-exercise__heading">
                      <h4>{isEnglish ? item.exercise.name_en : item.exercise.name_fa}</h4>
                      {isSuperset && <span>{t("workoutPlan.superset")}</span>}
                    </div>
                    {isSupersetStart && (
                      <p className="workout-exercise__superset-instruction">
                        {t("workoutPlan.supersetInstruction")}
                      </p>
                    )}
                    <dl>
                      <div><dt>{t("workoutPlan.sets")}</dt><dd>{item.sets}</dd></div>
                      <div><dt>{item.prescription_mode === "duration" ? t("workoutPlan.durationTarget") : t("workoutPlan.reps")}</dt><dd>{formatPrescriptionTarget(item, isEnglish ? "en" : "fa")}</dd></div>
                      <div><dt>{t("workoutPlan.rest")}</dt><dd>{item.rest_seconds}{t("workoutPlan.seconds")}</dd></div>
                      {item.rir !== null && <div><dt>{t("workoutPlan.rir")}</dt><dd>{item.rir}</dd></div>}
                    </dl>
                    {(isEnglish ? item.notes_en : item.notes_fa) !== null && (
                      <p>{isEnglish ? item.notes_en : item.notes_fa}</p>
                    )}
                    <Link to={`/exercises/${item.exercise.slug}`}>{t("workoutPlan.detail")}</Link>
                    {item.alternatives.length > 0 && (
                      <details className="workout-alternatives">
                        <summary>{t("workoutPlan.alternatives")}</summary>
                        {interactive
                          ? <WorkoutExerciseReplacementFlow item={item} isEnglish={isEnglish} />
                          : <AlternativeLinks item={item} isEnglish={isEnglish} />}
                      </details>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        );
        return (
        <details
          className={
            "workout-day"
            + (isFocused ? " workout-day--focus" : "")
            + (isNext ? " workout-day--next" : "")
          }
          data-workout-day-id={day.id}
          key={day.id ?? day.day_number}
          role="listitem"
        >
          <summary>
            {isFocused && leadExercise?.exercise.media_path && <span className="workout-day__media"><ExerciseMedia ambient path={leadExercise.exercise.media_path} name={isEnglish ? leadExercise.exercise.name_en : leadExercise.exercise.name_fa} mediaType={leadExercise.exercise.media_type} /></span>}
            <span>{String(day.day_number).padStart(2, "0")}</span>
            <div>
              {focusLabel !== null && <small>{focusLabel}</small>}
              <h3>{isEnglish ? day.title_en : day.title_fa}</h3>
              <p>{isFocused && leadExercise ? (isEnglish ? leadExercise.exercise.name_en : leadExercise.exercise.name_fa) + " · " : ""}{t("workoutPlan.sessionMinutes", { count: day.estimated_duration_minutes })}</p>
            </div>
          </summary>
          {day.ai_coach_explanation_fa && (
            <aside className="workout-ai-coach workout-ai-coach--day">
              <span className="workout-ai-coach__icon" aria-hidden="true">✦</span>
              <div><p>{t("workoutPlan.aiCoach")}</p><strong>{day.ai_coach_explanation_fa}</strong></div>
            </aside>
          )}
          {renderExercises(mainExercises)}
          {coreExercises.length > 0 && (
            <section className="workout-day__section" aria-labelledby={`workout-day-${day.day_number}-core-title`}>
              <h4 id={`workout-day-${day.day_number}-core-title`}>Core</h4>
              {renderExercises(coreExercises)}
            </section>
          )}
        </details>
        );
      })}
    </div>
  );
}

const replacementReasons: Array<{ value: WorkoutExerciseReplacementReason; fa: string; en: string }> = [
  { value: "equipment_unavailable", fa: "تجهیزاتش را ندارم", en: "I don't have the equipment" },
  { value: "uncomfortable", fa: "با این حرکت راحت نیستم", en: "This movement feels uncomfortable" },
  { value: "pain_or_discomfort", fa: "درد یا ناراحتی دارم", en: "I have pain or discomfort" },
  { value: "temporary_unavailable", fa: "فعلاً دستگاه/محل در دسترس نیست", en: "The equipment or place is temporarily unavailable" },
  { value: "dislike", fa: "این حرکت را دوست ندارم", en: "I don't like this movement" },
  { value: "other", fa: "دلیل دیگر", en: "Another reason" },
];

const replacementScopes: Array<{ value: WorkoutExerciseReplacementScope; fa: string; en: string }> = [
  { value: "this_time", fa: "فقط همین بار", en: "Just this time" },
  { value: "persistent", fa: "از این به بعد", en: "From now on" },
];

function AlternativeLinks({ item, isEnglish }: { item: WorkoutPlanExercise; isEnglish: boolean }) {
  return (
    <ul>
      {item.alternatives.map((alternative) => (
        <li key={alternative.exercise.id}>
          <Link to={`/exercises/${alternative.exercise.slug}`}>
            {isEnglish ? alternative.exercise.name_en : alternative.exercise.name_fa}
          </Link>
          <span>{isEnglish ? alternative.reason_en : alternative.reason_fa}</span>
        </li>
      ))}
    </ul>
  );
}

function WorkoutExerciseReplacementFlow({ item, isEnglish }: { item: WorkoutPlanExercise; isEnglish: boolean }) {
  const [reason, setReason] = useState<WorkoutExerciseReplacementReason | null>(null);
  const [alternativeId, setAlternativeId] = useState<string | null>(null);
  const [step, setStep] = useState<"reason" | "alternative" | "scope" | "success">("reason");
  const [error, setError] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const l = (fa: string, en: string) => isEnglish ? en : fa;
  const selectedAlternative = item.alternatives.find(({ exercise }) => exercise.id === alternativeId)?.exercise;

  function chooseReason(value: WorkoutExerciseReplacementReason) {
    setReason(value);
    setAlternativeId(null);
    setError(false);
    setStep("alternative");
  }

  function chooseAlternative(value: string) {
    setAlternativeId(value);
    setError(false);
    setStep("scope");
  }

  function submit(selectedScope: WorkoutExerciseReplacementScope) {
    if (reason === null || alternativeId === null) return;
    setError(false);
    setSubmitting(true);
    void recordExerciseReplacement({
      workout_plan_exercise_id: item.id,
      replacement_exercise_id: alternativeId,
      reason,
      scope: selectedScope,
    })
      .then(() => setStep("success"))
      .catch(() => {
        setError(true);
        setStep("scope");
      })
      .finally(() => setSubmitting(false));
  }

  if (step === "success" && selectedAlternative !== undefined) {
    return (
      <p className="workout-replacement-success" role="status">
        {l("جایگزین انتخاب‌شده", "Selected replacement")}: {isEnglish ? selectedAlternative.name_en : selectedAlternative.name_fa}
      </p>
    );
  }

  return (
    <div className="workout-replacement-flow">
      {step === "reason" && <p>{l("اول دلیل تعویض را انتخاب کن.", "First, choose why you want to replace it.")}</p>}
      {error && <p className="workout-replacement-error" role="alert">{l("ثبت جایگزین انجام نشد؛ دوباره تلاش کن.", "The replacement could not be saved. Try again.")}</p>}
      {step === "reason" && (
        <div className="workout-replacement-options" role="group" aria-label={l("دلیل تعویض", "Replacement reason")}>
          {replacementReasons.map((option) => (
            <button type="button" key={option.value} onClick={() => chooseReason(option.value)}>
              {l(option.fa, option.en)}
            </button>
          ))}
        </div>
      )}
      {step === "alternative" && (
        <>
          <p>{l("حالا یک حرکت امن از فهرست زیر انتخاب کن.", "Now choose a safe movement from the list below.")}</p>
          <div className="workout-replacement-options" role="group" aria-label={l("حرکت‌های جایگزین امن", "Safe alternatives")}>
            {item.alternatives.map((alternative) => (
              <button
                type="button"
                key={alternative.exercise.id}
                aria-label={isEnglish ? alternative.exercise.name_en : alternative.exercise.name_fa}
                onClick={() => chooseAlternative(alternative.exercise.id)}
              >
                {isEnglish ? alternative.exercise.name_en : alternative.exercise.name_fa}
                <span>{isEnglish ? alternative.reason_en : alternative.reason_fa}</span>
              </button>
            ))}
          </div>
        </>
      )}
      {step === "scope" && selectedAlternative !== undefined && (
        <>
          <p>{l(`برای «${selectedAlternative.name_fa}» این تعویض تا چه زمانی باشد؟`, `How long should “${selectedAlternative.name_en}” replace this movement?`)}</p>
          <div className="workout-replacement-options" role="group" aria-label={l("مدت جایگزینی", "Replacement scope")}>
            {replacementScopes.map((option) => (
              <button type="button" key={option.value} disabled={submitting} onClick={() => submit(option.value)}>
                {l(option.fa, option.en)}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

function FixedGuidance() {
  const { t } = useTranslation();
  return (
    <aside className="workout-guidance" aria-labelledby="workout-guidance-title">
      <div><span aria-hidden="true">↗</span><h2 id="workout-guidance-title">{t("workoutPlan.beforeStart")}</h2></div>
      <ul>
        {(["form", "warmup", "progress", "recovery", "pain"] as const).map((item) => (
          <li key={item}>{t(`workoutPlan.guidance.${item}`)}</li>
        ))}
      </ul>
    </aside>
  );
}

function GenerateButton({ generating, onClick, update = false, disabled = false }: { generating: boolean; onClick: () => void; update?: boolean; disabled?: boolean }) {
  const { t } = useTranslation();
  return <button className="workout-generate" type="button" disabled={generating || disabled} onClick={onClick}>{generating ? t("workoutPlan.generating") : t(update ? "workoutPlan.update" : "workoutPlan.generate")}</button>;
}

function AccessLockedNotice() {
  const { t } = useTranslation();
  return (
    <p className="workout-status" role="status">
      <strong>{t("entitlements.lockedAction")}</strong> {t("entitlements.upgradeHint")}
    </p>
  );
}

function StatusPanel({ role, message, action, onAction }: { role: "status" | "alert"; message: string; action?: string; onAction?: () => void }) {
  return <section className="workout-status" role={role}><p>{message}</p>{action !== undefined && onAction !== undefined && <button type="button" onClick={onAction}>{action}</button>}</section>;
}
