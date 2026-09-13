import {
  nutritionProgressTone,
  nutritionTargetToExpenditureRatio,
  type NutritionProgressTone,
} from "@fitician/core";
import { localIsoDate, resolvedIanaTimeZone } from "@fitician/core/local-date";
import type { ProgramTimelineToday, TimelineWorkoutSession, WorkoutTimelineState } from "@fitician/core/program-timeline";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useNavigate } from "react-router-dom";

import bodyAnalysisImage from "../assets/landing/body.webp";
import foodAnalysisImage from "../assets/landing/food.webp";
import { useAuth } from "../features/auth/AuthContext";
import { useEntitlements } from "../features/entitlements/EntitlementContext";
import { ExerciseMedia } from "../features/exercises/ExerciseMedia";
import { getCurrentNutritionEstimate, getDailyTracking, getLatestWeeklyNutritionPlan } from "../features/nutrition/api";
import type { DailyTrackingSummary, NutritionEstimate, WeeklyPlan } from "../features/nutrition/types";
import { getProgramTimelineToday } from "../features/programTimeline/api";
import { useProfile } from "../features/profile/ProfileContext";
import { generateWorkoutPlan, getActiveWorkoutPlan } from "../features/workouts/api";
import type { WorkoutPlan } from "../features/workouts/types";
import { ProgressRing } from "../shared/ProgressRing";
import "./dashboard.css";

type PlanState = "loading" | "empty" | "ready" | "error";
type NutritionState = "loading" | "pending" | "ready" | "empty";

const nutritionRingColors: Record<NutritionProgressTone, string> = {
  blue: "var(--fitician-blue)",
  green: "var(--fitician-success)",
  red: "var(--fitician-danger)",
};

export function DashboardPage() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { profile, productMode } = useProfile();
  const { loading: entitlementsLoading, hasEntitlement } = useEntitlements();
  const canGenerateWorkout = hasEntitlement("training.plan.generate");
  const hasTraining = productMode === undefined || productMode === "training" || productMode === "both";
  const hasNutrition = productMode === "nutrition" || productMode === "both";
  const [planState, setPlanState] = useState<PlanState>("loading");
  const [plan, setPlan] = useState<WorkoutPlan | null>(null);
  const [generating, setGenerating] = useState(false);
  const [nutritionState, setNutritionState] = useState<NutritionState>("loading");
  const [nutritionPlan, setNutritionPlan] = useState<WeeklyPlan | null>(null);
  const [nutritionEstimate, setNutritionEstimate] = useState<NutritionEstimate | null>(null);
  const [dailyTracking, setDailyTracking] = useState<DailyTrackingSummary | null>(null);
  const [timeline, setTimeline] = useState<ProgramTimelineToday | null>(null);
  const [deviceTimezone] = useState(() => resolvedIanaTimeZone());

  useEffect(() => {
    if (!hasTraining) {
      setPlanState("empty");
      return;
    }
    let active = true;
    void getActiveWorkoutPlan()
      .then((activePlan) => {
        if (!active) return;
        setPlan(activePlan);
        setPlanState(activePlan === null ? "empty" : "ready");
      })
      .catch(() => { if (active) setPlanState("error"); });
    return () => { active = false; };
  }, [hasTraining]);

  useEffect(() => {
    let active = true;
    void getProgramTimelineToday(deviceTimezone)
      .then((loadedTimeline) => {
        if (active && loadedTimeline !== undefined) setTimeline(loadedTimeline);
      })
      .catch(() => undefined);
    return () => { active = false; };
  }, [deviceTimezone]);

  useEffect(() => {
    if (!hasNutrition) {
      setNutritionState("empty");
      return;
    }
    let active = true;
    void Promise.all([
      getLatestWeeklyNutritionPlan(),
      getCurrentNutritionEstimate(),
    ])
      .then(([latestPlan, estimate]) => {
        if (active) {
          setNutritionPlan(latestPlan);
          setNutritionEstimate(estimate);
          setNutritionState(latestPlan !== null
            ? latestPlan.physician_review_required === true && !latestPlan.physician_approved ? "pending" : "ready"
            : estimate !== null ? "ready" : "empty");
        }
    })
      .catch(() => { if (active) setNutritionState("empty"); });
    return () => { active = false; };
  }, [hasNutrition]);

  useEffect(() => {
    if (!hasNutrition) return;
    let active = true;
    const date = timeline?.local_date ?? localIsoDate();
    void getDailyTracking(date)
      .catch(() => null)
      .then((tracking) => {
        if (active) setDailyTracking(tracking);
      });
    return () => { active = false; };
  }, [hasNutrition, timeline?.local_date]);

  if (user === null) return null;

  function startWorkout() {
    if (!canGenerateWorkout || entitlementsLoading) return;
    setGenerating(true);
    void generateWorkoutPlan()
      .then(() => navigate("/workout-plan"))
      .finally(() => setGenerating(false));
  }

  const english = i18n.resolvedLanguage === "en";
  const planDuration = profile?.plan_duration_weeks;
  const locale = english ? "en-US" : "fa-IR";
  const currentDate = timeline?.local_date ?? localIsoDate();
  const timelineWorkout = timeline !== null
    && plan !== null
    && timeline.workout.workout_plan_id === plan.id
    ? timeline.workout
    : null;
  const workoutState: WorkoutTimelineState = plan === null
    ? "no_plan"
    : timelineWorkout?.state ?? "ready_to_start";
  const workoutSession = workoutState === "overdue"
    ? timelineWorkout?.overdue_session
    : workoutState === "workout_today" || workoutState === "completed_today"
      ? timelineWorkout?.today_session
      : null;
  const workoutDay = workoutSession === undefined || workoutSession === null
    ? undefined
    : plan?.days.find((day) => day.id === workoutSession.workout_day_id);
  const planned = timeline !== null
    && (timeline.nutrition.state === "active" || timeline.nutrition.state === "scheduled_start")
    ? timeline.nutrition.nutrient_totals
    : timeline === null
      ? nutritionPlan?.days?.find((day) => day.plan_date === currentDate)?.nutrient_totals
      : undefined;
  const estimated = nutritionEstimate?.targets;
  const tdeeTarget = estimated?.tdee?.preferred ?? estimated?.tdee?.minimum ?? null;
  const nutritionTarget = {
    energy_kcal: planned?.energy_kcal ?? estimated?.goal_calories?.preferred ?? null,
    protein_g: planned?.protein_g ?? estimated?.protein?.preferred ?? null,
    carbohydrate_g: planned?.carbohydrate_g ?? estimated?.carbohydrate?.preferred ?? null,
    total_fat_g: planned?.total_fat_g ?? estimated?.total_fat?.preferred ?? null,
  };
  const trackedTotals = dailyTracking?.actual_totals;
  const hasActual = trackedTotals !== undefined && (
    dailyTracking?.data_status === "sufficient"
    || (dailyTracking?.entries?.length ?? 0) > 0
    || Object.values(trackedTotals).some((value) => value > 0)
  );
  const actual = hasActual ? trackedTotals : null;
  const hasNutritionTarget = nutritionTarget.energy_kcal !== null;
  const nutritionProgress = nutritionTargetToExpenditureRatio(nutritionTarget.energy_kcal, tdeeTarget);
  const nutritionTone = nutritionProgressTone(nutritionProgress);
  const aboveExpenditureCalories = nutritionTarget.energy_kcal !== null && tdeeTarget !== null
    ? Math.max(0, nutritionTarget.energy_kcal - tdeeTarget)
    : 0;
  const format = (value: number) => Math.round(value).toLocaleString(locale);
  const displayName = profile?.display_name ?? (english ? "there" : "دوست");
  const avatarInitial = displayName.trim().charAt(0).toLocaleUpperCase(locale);

  return (
    <main className="command-center fitician-page">
      <div className="command-center__container">
        <header className="command-center__welcome">
          <Link className="command-center__avatar" to="/profile" aria-label={t("header.profile")}>
            {avatarInitial}
          </Link>
          <div>
            <h1 className="fitician-display">{t("dashboard.greeting", { name: displayName })}</h1>
            <p>{english ? "Ready for today?" : "برای امروز آماده‌ای؟"}</p>
          </div>
          <span className="command-center__live" aria-hidden="true" />
        </header>

        {profile === null && (
          <Link className="fitician-button" to="/onboarding">{t("dashboard.completeProfile")}</Link>
        )}

        <section className="command-center__grid" aria-label={t("dashboard.statusLabel")}>
          {hasTraining && (
            <article className="command-card command-card--primary" role="region" aria-labelledby="dashboard-today-workout">
              <div className="command-card__head">
                <div>
                  <p>{t("dashboard.trainingEyebrow")}</p>
                  <h2 id="dashboard-today-workout">
                    {workoutState === "ready_to_start" && t("dashboard.programReady")}
                    {workoutState === "scheduled_start" && t("dashboard.programScheduled")}
                    {workoutState === "workout_today" && t("dashboard.todayWorkout")}
                    {workoutState === "rest_day" && t("dashboard.restDay")}
                    {workoutState === "overdue" && t("dashboard.overdue")}
                    {workoutState === "completed_today" && t("dashboard.completedToday")}
                    {workoutState === "legacy_cycle" && t("dashboard.legacyCycle")}
                    {workoutState === "cycle_completed" && t("dashboard.cycleCompleted")}
                    {workoutState === "no_plan" && t("dashboard.todayWorkout")}
                  </h2>
                </div>
                <span className={"fitician-status fitician-status--" + (workoutState === "workout_today" || workoutState === "completed_today" ? "success" : "neutral")}>
                  {workoutState === "no_plan" ? t(`dashboard.planState.${planState}`) : t(`dashboard.workoutState.${workoutState}`)}
                </span>
              </div>
              {workoutDay !== undefined && workoutSession !== null && workoutSession !== undefined ? (
                <>
                  <div className="command-card__workout">
                    <span>{String(workoutDay.day_number).padStart(2, "0")}</span>
                    <div>
                      <h3>{english ? workoutDay.title_en : workoutDay.title_fa}</h3>
                      <p>{t("dashboard.sessionMinutes", { count: format(workoutDay.estimated_duration_minutes) })} · {t("dashboard.sessionNumber", { count: workoutSession.session_number })}</p>
                    </div>
                  </div>
                  {workoutDay.exercises[0]?.exercise.media_path && <div className="command-card__media"><ExerciseMedia ambient path={workoutDay.exercises[0].exercise.media_path} name={english ? workoutDay.exercises[0].exercise.name_en : workoutDay.exercises[0].exercise.name_fa} mediaType={workoutDay.exercises[0].exercise.media_type} /></div>}
                </>
              ) : workoutState === "rest_day" ? (
                <>
                  <p className="command-card__context">{t("dashboard.restDayBody")}</p>
                  {timelineWorkout?.next_session && <p className="command-card__context">{nextSessionCopy(timelineWorkout.next_session, english)}</p>}
                </>
              ) : workoutState === "overdue" ? (
                <>
                  <p className="command-card__context">{t("dashboard.overdueBody")}</p>
                  {timelineWorkout?.overdue_session && <p className="command-card__context">{t("dashboard.originallyScheduled", { date: formatTimelineDate(timelineWorkout.overdue_session.scheduled_date, english), session: timelineWorkout.overdue_session.session_number })}</p>}
                </>
              ) : workoutState === "completed_today" ? (
                <>
                  <p className="command-card__context">{t("dashboard.completedTodayBody")}</p>
                  {timelineWorkout?.next_session && <p className="command-card__context">{nextSessionCopy(timelineWorkout.next_session, english)}</p>}
                </>
              ) : workoutState === "scheduled_start" && timelineWorkout?.start_date ? (
                <p className="command-card__context">{t("dashboard.programStartsOn", { date: formatTimelineDate(timelineWorkout.start_date, english) })}</p>
              ) : workoutState === "ready_to_start" ? (
                <p className="command-card__context">{t("dashboard.programReadyBody")}</p>
              ) : workoutState === "legacy_cycle" ? (
                <p className="command-card__context">{t("dashboard.legacyCycleBody")}</p>
              ) : workoutState === "cycle_completed" ? (
                <p className="command-card__context">{t("dashboard.cycleCompletedBody")}</p>
              ) : planDuration !== undefined ? <p className="command-card__context">{t("dashboard.planDuration", { count: planDuration.toLocaleString(locale) })}</p> : null}
              <PrimaryAction
                accessLoading={entitlementsLoading}
                canGenerate={canGenerateWorkout}
                state={planState}
                hasPlan={plan !== null}
                timelineState={workoutState}
                generating={generating}
                onStart={startWorkout}
              />
            </article>
          )}

          {hasNutrition && (
            <Link
              className="command-card command-card--nutrition"
              to="/nutrition-estimate"
              aria-label={t("dashboard.nutritionAria")}
            >
              <div className="command-card__head"><div><p>{t("dashboard.nutritionEyebrow")}</p><h2>{t("dashboard.nutritionTitle")}</h2></div><span className="command-card__arrow" aria-hidden="true">←</span></div>
              {hasNutritionTarget ? <>
                <div className="command-card__calories">
                  <div className="command-card__calorie-values">
                    <div><strong>{format(nutritionTarget.energy_kcal ?? 0)}</strong><span>{english ? "daily target" : "هدف روزانه"}</span></div>
                    {tdeeTarget !== null && <div><strong>{format(tdeeTarget)}</strong><span>{english ? "Estimated daily expenditure" : "مصرف تقریبی روزانه"}</span></div>}
                  </div>
                  <ProgressRing
                    animateOnMount
                    color={nutritionRingColors[nutritionTone]}
                    value={nutritionTarget.energy_kcal ?? 0}
                    max={tdeeTarget ?? 0}
                    label={english ? "Today's calorie progress" : "پیشرفت کالری امروز"}
                  />
                </div>
                {aboveExpenditureCalories > 0 && <p className="command-card__overage">{english ? `${format(aboveExpenditureCalories)} kcal above estimated daily expenditure` : `${format(aboveExpenditureCalories)} کیلوکالری بالاتر از مصرف تقریبی روزانه`}</p>}
                <div className="fitician-metric-strip">
                  <span><strong>{formatMetric(actual?.protein_g ?? nutritionTarget.protein_g, format)}</strong><small>{english ? "Protein" : "پروتئین"}</small></span>
                  <span><strong>{formatMetric(actual?.carbohydrate_g ?? nutritionTarget.carbohydrate_g, format)}</strong><small>{english ? "Carbs" : "کربوهیدرات"}</small></span>
                  <span><strong>{formatMetric(actual?.total_fat_g ?? nutritionTarget.total_fat_g, format)}</strong><small>{english ? "Fat" : "چربی"}</small></span>
                </div>
              </> : <span className="command-card__empty">{t(`dashboard.nutritionState.${nutritionState}`)}</span>}
            </Link>
          )}

        </section>

        <nav className="command-center__quick" aria-label={t("dashboard.quickActions") }>
          <DashboardQuickAction
            image={bodyAnalysisImage}
            title="body analys"
            to="/body-progress"
          />
          {hasNutrition && (
            <DashboardQuickAction
              image={foodAnalysisImage}
              title="food analys"
              to="/nutrition-tracking"
            />
          )}
        </nav>
      </div>
    </main>
  );
}

function DashboardQuickAction({ image, title, to }: { image: string; title: string; to: string }) {
  return (
    <Link className="command-quick-card" to={to} aria-label={title}>
      <img src={image} alt="" />
      <i className="command-quick-card__scan" aria-hidden="true" />
      <span dir="ltr">{title}</span>
    </Link>
  );
}

function formatTimelineDate(value: string, english: boolean): string {
  return new Intl.DateTimeFormat(english ? "en-US" : "fa-IR", { dateStyle: "medium" }).format(
    new Date(value + "T12:00:00"),
  );
}

function nextSessionCopy(session: TimelineWorkoutSession, english: boolean): string {
  const date = formatTimelineDate(session.scheduled_date, english);
  return english
    ? "Next: " + date + " · Session " + session.session_number
    : "جلسه بعد: " + date + " · جلسه " + session.session_number;
}

function formatMetric(value: number | null | undefined, format: (value: number) => string) {
  return value === null || value === undefined ? "—" : `${format(value)}g`;
}

function PrimaryAction({
  accessLoading,
  canGenerate,
  state,
  hasPlan,
  timelineState,
  generating,
  onStart,
}: {
  accessLoading: boolean;
  canGenerate: boolean;
  state: PlanState;
  hasPlan: boolean;
  timelineState: WorkoutTimelineState;
  generating: boolean;
  onStart: () => void;
}) {
  const { t } = useTranslation();
  if (hasPlan) {
    return (
      <Link className="fitician-button command-card__action" to="/workout-plan">
        {t(timelineState === "ready_to_start" ? "dashboard.startProgram" : "dashboard.viewWorkout")}
      </Link>
    );
  }
  if (state === "ready") {
    return <Link className="fitician-button command-card__action" to="/workout-plan">{t("dashboard.start")}</Link>;
  }
  if (!accessLoading && !canGenerate) {
    return (
      <div className="command-card__locked" role="status">
        <strong>{t("entitlements.lockedAction")}</strong>
        <small>{t("entitlements.upgradeHint")}</small>
      </div>
    );
  }
  return (
    <button className="fitician-button command-card__action" type="button" onClick={onStart} disabled={state === "loading" || generating}>
      {generating ? t("dashboard.generating") : t("dashboard.start")}
    </button>
  );
}
