import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { formatTehranDateTime } from "@fitician/core";
import { useEffect, useMemo, useRef, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { workoutKeys } from "../data/queryKeys";
import { connectivityMonitor, type ConnectivityStatus } from "../platform/connectivity";
import {
  AppIcon,
  Button,
  Card,
  Notice,
  Skeleton,
  TextField,
} from "../ui/components";
import { formatPersianNumber } from "../ui/locale";
import { getMobileViewState, mobileRequestErrorMessage, type MobileViewState } from "../ui/requestState";
import { fiticianTokens } from "../ui/tokens";
import type { WorkoutPlan, WorkoutPlanExercise } from "./workoutApi";
import {
  createWorkoutCycleApi,
  type WorkoutCycleApi,
  type WorkoutCycleCompletionFeedback,
  type WorkoutCycleCurrent,
} from "./workoutCycleApi";
import {
  completionFeedbackFormFromResponse,
  emptyCompletionFeedbackForm,
  emptyWeeklyCheckInForm,
  toCompletionFeedbackInput,
  toWeeklyCheckInInput,
  weeklyCheckInFormFromResponse,
  type CompletionFeedbackForm,
  type WeeklyCheckInForm,
} from "./workoutCycleModel";
import { workoutCycleWeekDisplay } from "./workoutModel";
import type { TimelineWorkout } from "@fitician/core/program-timeline";
import { WorkoutTimelineCard, type WorkoutTimelineCardProps } from "./WorkoutTimelineCard";

type Choice<TValue extends string> = {
  readonly label: string;
  readonly description?: string;
  readonly value: TValue;
};

type WorkoutDifficulty = "too_easy" | "easy" | "appropriate" | "hard" | "too_hard";
type ReplacementReason = "equipment_unavailable" | "uncomfortable" | "pain_or_discomfort" | "temporary_unavailable" | "dislike" | "other";

const difficultyChoices: readonly Choice<WorkoutDifficulty>[] = [
  { label: "خیلی سبک", value: "too_easy" },
  { label: "سبک", value: "easy" },
  { label: "مناسب", value: "appropriate" },
  { label: "سنگین", value: "hard" },
  { label: "خیلی سنگین", value: "too_hard" },
];

const recoveryChoices: readonly Choice<"good" | "average" | "poor">[] = [
  { label: "خوب", value: "good" },
  { label: "متوسط", value: "average" },
  { label: "ضعیف", value: "poor" },
];

const satisfactionChoices: readonly Choice<"very_dissatisfied" | "dissatisfied" | "neutral" | "satisfied" | "very_satisfied">[] = [
  { label: "خیلی ناراضی", value: "very_dissatisfied" },
  { label: "ناراضی", value: "dissatisfied" },
  { label: "معمولی", value: "neutral" },
  { label: "راضی", value: "satisfied" },
  { label: "خیلی راضی", value: "very_satisfied" },
];

const progressChoices: readonly Choice<"declined" | "unchanged" | "improved">[] = [
  { label: "کمتر شد", value: "declined" },
  { label: "بدون تغییر", value: "unchanged" },
  { label: "بهتر شد", value: "improved" },
];

const replacementReasons: readonly Choice<ReplacementReason>[] = [
  { label: "تجهیزاتش را ندارم", value: "equipment_unavailable" },
  { label: "با این حرکت راحت نیستم", value: "uncomfortable" },
  { label: "درد یا ناراحتی دارم", value: "pain_or_discomfort" },
  { label: "فعلاً دستگاه/محل در دسترس نیست", value: "temporary_unavailable" },
  { label: "این حرکت را دوست ندارم", value: "dislike" },
  { label: "دلیل دیگر", value: "other" },
];

const replacementScopes: readonly Choice<"this_time" | "persistent">[] = [
  { label: "فقط همین بار", value: "this_time" },
  { label: "از این به بعد", value: "persistent" },
];

export function WorkoutCyclePanel({
  expectedCycleId,
  plan,
  timeline,
  timelineCardProps,
}: {
  readonly expectedCycleId?: string;
  readonly plan: WorkoutPlan;
  readonly timeline?: TimelineWorkout | null;
  readonly timelineCardProps?: Omit<WorkoutTimelineCardProps, "timeline">;
}) {
  const auth = useMobileAuth();
  const connectivityStatus = useConnectivityStatus();
  const api = useMemo(
    () => createWorkoutCycleApi(auth.request),
    [auth.request],
  );
  const cycleQuery = useQuery({
    queryFn: api.getCurrent,
    queryKey: workoutKeys.currentCycle(),
  });
  const cycleState = getMobileViewState(cycleQuery, { context: "workout", connectivityStatus });
  const cycle = viewData(cycleState);

  if (cycleState.status === "loading") return <Skeleton height={140} />;
  if (cycleState.status === "error" && cycle === undefined) {
    return (
      <Notice
        actionLabel="تلاش دوباره"
        message="چرخهٔ فعلی دریافت نشد."
        onAction={() => void cycleQuery.refetch()}
        variant="danger"
      />
    );
  }
  if (cycleState.status === "offline" && cycle === undefined) {
    return <Notice message="برای دریافت چرخهٔ فعلی به اینترنت وصل شو." variant="offline" />;
  }
  if (cycle === undefined || cycle === null) {
    return <Notice message="برای این برنامه چرخهٔ فعالی پیدا نشد." variant="info" />;
  }
  if (cycle.workout_plan_id !== plan.id) {
    return <Notice message="چرخهٔ فعلی با این نسخهٔ برنامه هماهنگ نیست." variant="warning" />;
  }
  if (expectedCycleId !== undefined && cycle.cycle_id !== expectedCycleId) {
    return <Notice message="این چرخه دیگر چرخهٔ فعلی نیست یا در دسترس نیست." variant="warning" />;
  }

  return (
    <View style={styles.panel} testID="workout-cycle-panel">
      {timeline !== undefined && timeline !== null && timelineCardProps !== undefined ? (
        <WorkoutTimelineCard timeline={timeline} {...timelineCardProps} />
      ) : null}
      {cycleState.status === "stale" ? (
        <Notice message="اطلاعات چرخه تازه‌سازی نشده است." variant="warning" />
      ) : null}
      <CycleSummary cycle={cycle} />
      {cycle.status === "active" ? (
        <>
          <WeeklyCheckInPanel
            api={api}
            connectivityStatus={connectivityStatus}
            plan={plan}
            cycle={cycle}
          />
        </>
      ) : null}
    </View>
  );
}

function CycleSummary({ cycle }: { readonly cycle: WorkoutCycleCurrent }) {
  const week = workoutCycleWeekDisplay(cycle);
  return (
    <View style={styles.summaryCard}>
      <View style={styles.summaryHeading}>
        <View style={styles.summaryCopy}>
          <Text style={styles.sectionEyebrow}>چرخهٔ تمرین</Text>
          <Text style={styles.sectionTitle}>چرخهٔ فعلی</Text>
        </View>
        <Text style={styles.cycleStatus}>{cycle.status === "active" ? "فعال" : "تکمیل‌شده"}</Text>
      </View>
      <View style={styles.summaryMetrics}>
        <View style={styles.summaryMetric}>
          <Text style={styles.summaryMetricLabel}>هفته فعلی</Text>
          <Text style={styles.summaryMetricValueAqua}>{week.currentWeek}</Text>
        </View>
        <View style={styles.summaryMetricDivider} />
        <View style={styles.summaryMetric}>
          <Text style={styles.summaryMetricLabel}>کل چرخه</Text>
          <Text style={styles.summaryMetricValue}>{week.durationWeeks} هفته</Text>
        </View>
        <View style={styles.summaryMetricDivider} />
        <View style={styles.summaryMetric}>
          <Text style={styles.summaryMetricLabel}>شروع</Text>
          <Text numberOfLines={1} style={styles.summaryMetricValue}>{formatDate(cycle.started_at)}</Text>
        </View>
      </View>
    </View>
  );
}

function WeeklyCheckInPanel({
  api,
  connectivityStatus,
  cycle,
  plan,
}: {
  readonly api: WorkoutCycleApi;
  readonly connectivityStatus: ConnectivityStatus;
  readonly cycle: WorkoutCycleCurrent;
  readonly plan: WorkoutPlan;
}) {
  const queryClient = useQueryClient();
  const queryKey = workoutKeys.weeklyCheckIn(cycle.cycle_id);
  const query = useQuery({ queryFn: api.getWeeklyCheckIn, queryKey });
  const state = getMobileViewState(query, { context: "workout", connectivityStatus });
  const checkIn = viewData(state);
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState<WeeklyCheckInForm>(emptyWeeklyCheckInForm);
  const [formError, setFormError] = useState<string | null>(null);
  const save = useMutation({
    mutationFn: api.saveWeeklyCheckIn,
    onError: (error: unknown) => setFormError(mobileRequestErrorMessage(
      error,
      "ثبت چک‌این انجام نشد؛ دوباره تلاش کن.",
      { audience: "member", context: "workout" },
    )),
    onSuccess: (saved) => {
      queryClient.setQueryData(queryKey, saved);
      setForm(weeklyCheckInFormFromResponse(saved));
      setEditing(false);
      setFormError(null);
    },
  });

  useEffect(() => {
    if (checkIn !== undefined) {
      setForm(weeklyCheckInFormFromResponse(checkIn));
      setEditing(checkIn === null);
    }
  }, [checkIn]);

  if (state.status === "loading") return <Skeleton height={190} />;
  if (state.status === "error" && checkIn === undefined) {
    return (
      <Notice
        actionLabel="تلاش دوباره"
        message={state.error.message}
        onAction={() => void query.refetch()}
        variant="danger"
      />
    );
  }
  if (state.status === "offline" && checkIn === undefined) {
    return <Notice message="برای دریافت یا ثبت چک‌این هفتگی به اینترنت وصل شو." variant="offline" />;
  }
  if (checkIn === undefined) return null;
  if (checkIn !== null && !editing) {
    return (
      <Card style={styles.feedbackCard}>
        <Text style={styles.sectionTitle}>چک‌این هفتگی</Text>
        <Text style={styles.successText}>چک‌این هفتهٔ {checkIn.week_number} ثبت شده است.</Text>
        <Text style={styles.bodyText}>
          {checkIn.sessions_completed} جلسه · {difficultyLabel(checkIn.perceived_difficulty)} · ریکاوری {recoveryLabel(checkIn.recovery_rating)}
        </Text>
        {checkIn.has_pain_or_limitation ? <Notice message="محدودیت یا درد ثبت شده است؛ قبل از ادامه با دقت تمرین کن." variant="warning" /> : null}
        <Button label="ویرایش چک‌این" onPress={() => setEditing(true)} variant="ghost" />
      </Card>
    );
  }

  const exercises = plan.days.flatMap((day) => day.exercises);
  const sessions = Array.from({ length: plan.days.length + 1 }, (_, value) => value);
  const offline = connectivityStatus === "offline";

  function submit() {
    if (form.hasPainOrLimitation && form.affectedExerciseId === "") {
      setFormError("اگر درد یا محدودیت داری، حرکت مرتبط را انتخاب کن.");
      return;
    }
    if (offline) {
      setFormError("ثبت چک‌این بدون اینترنت انجام نمی‌شود.");
      return;
    }
    setFormError(null);
    save.mutate(toWeeklyCheckInInput(form));
  }

  return (
    <Card style={styles.formCard}>
      <View style={styles.formHeading}>
        <View style={styles.summaryCopy}>
          <Text style={styles.sectionEyebrow}>بازخورد هفته</Text>
          <Text style={styles.sectionTitle}>چک‌این هفتگی</Text>
        </View>
        <Text style={styles.weekBadge}>هفته {cycle.current_week}</Text>
      </View>
      <ChoiceGroup
        label="چند جلسه را کامل کردی؟"
        options={sessions.map((value) => ({ label: String(value), value: String(value) }))}
        selected={String(form.sessionsCompleted)}
        onSelect={(value) => setForm((current) => ({ ...current, sessionsCompleted: Number(value) }))}
      />
      <ChoiceGroup
        label="شدت تمرین‌ها چطور بود؟"
        options={difficultyChoices}
        selected={form.perceivedDifficulty}
        onSelect={(value) => setForm((current) => ({ ...current, perceivedDifficulty: value as WeeklyCheckInForm["perceivedDifficulty"] }))}
      />
      <ChoiceGroup
        label="ریکاوری‌ات چطور بود؟"
        options={recoveryChoices}
        selected={form.recoveryRating}
        onSelect={(value) => setForm((current) => ({ ...current, recoveryRating: value as WeeklyCheckInForm["recoveryRating"] }))}
      />
      <ChoiceGroup
        label="درد یا محدودیت داشتی؟"
        options={[{ label: "خیر", value: "false" }, { label: "بله", value: "true" }]}
        selected={String(form.hasPainOrLimitation)}
        onSelect={(value) => setForm((current) => ({
          ...current,
          affectedExerciseId: value === "true" ? current.affectedExerciseId : "",
          hasPainOrLimitation: value === "true",
        }))}
      />
      {form.hasPainOrLimitation ? (
        <View style={styles.formGroup}>
          <Text style={styles.fieldLabel}>حرکت مرتبط</Text>
          <ChoiceGroup
            label=""
            options={exercises.map((exercise) => ({
              label: exercise.exercise.name_fa || exercise.exercise.name_en,
              value: exercise.id,
            }))}
            selected={form.affectedExerciseId}
            onSelect={(value) => setForm((current) => ({ ...current, affectedExerciseId: value }))}
          />
          <TextField
            label="توضیح درد یا محدودیت"
            maxLength={500}
            multiline
            numberOfLines={3}
            onChangeText={(painNote) => setForm((current) => ({ ...current, painNote }))}
            value={form.painNote}
          />
        </View>
      ) : null}
      {state.status === "offline" ? <Notice message="این فرم از آخرین وضعیت ذخیره‌شده نمایش داده می‌شود." variant="offline" /> : null}
      {formError !== null ? <Notice message={formError} variant="danger" /> : null}
      <Button
        disabled={offline}
        label={editing && checkIn !== null ? "ذخیرهٔ تغییرات" : "ثبت چک‌این"}
        loading={save.isPending}
        onPress={submit}
      />
    </Card>
  );
}

export function WorkoutExerciseReplacementFlow({ item }: { readonly item: WorkoutPlanExercise }) {
  const auth = useMobileAuth();
  const api = useMemo(() => createWorkoutCycleApi(auth.request), [auth.request]);
  const connectivityStatus = useConnectivityStatus();
  const [reason, setReason] = useState<ReplacementReason | null>(null);
  const [alternativeId, setAlternativeId] = useState<string | null>(null);
  const [step, setStep] = useState<"reason" | "alternative" | "scope" | "success">("reason");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const submissionLocked = useRef(false);
  const selectedAlternative = item.alternatives.find(({ exercise }) => exercise.id === alternativeId);
  const offline = connectivityStatus === "offline";

  async function submit(scope: "this_time" | "persistent") {
    if (submissionLocked.current || reason === null || selectedAlternative === undefined) return;
    if (connectivityMonitor.getSnapshot().status === "offline") {
      setError("ثبت جایگزین بدون اینترنت انجام نمی‌شود.");
      return;
    }
    submissionLocked.current = true;
    setSubmitting(true);
    setError(null);
    try {
      await api.recordReplacement({
        reason,
        replacement_exercise_id: selectedAlternative.exercise.id,
        scope,
        workout_plan_exercise_id: item.id,
      });
      setStep("success");
    } catch (cause: unknown) {
      submissionLocked.current = false;
      setError(mobileRequestErrorMessage(cause, "ثبت جایگزین انجام نشد؛ دوباره تلاش کن.", {
        audience: "member", context: "workout",
      }));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <View accessibilityState={{ busy: submitting }} testID={`workout-replacement-${item.id}`}>
      <Card style={styles.formCard}>
        {step === "success" && selectedAlternative !== undefined ? (
          <Notice message={`جایگزین انتخاب‌شده: ${selectedAlternative.exercise.name_fa}`} variant="success" />
        ) : (
          <>
            {step === "reason" ? (
              <>
                <Text style={styles.bodyText}>اول دلیل تعویض را انتخاب کن.</Text>
                <ChoiceGroup
                  label="دلیل تعویض"
                  options={replacementReasons}
                  selected=""
                  onSelect={(value) => {
                    setReason(value);
                    setStep("alternative");
                  }}
                />
              </>
            ) : null}
            {step === "alternative" ? (
              <>
                <Text style={styles.bodyText}>حالا یک حرکت امن از فهرست زیر انتخاب کن.</Text>
                <ChoiceGroup
                  label="حرکت‌های جایگزین امن"
                  options={item.alternatives.map(({ exercise, reason_fa }) => ({
                    label: exercise.name_fa,
                    description: reason_fa,
                    value: exercise.id,
                  }))}
                  selected=""
                  onSelect={(value) => {
                    setAlternativeId(value);
                    setStep("scope");
                  }}
                />
              </>
            ) : null}
            {step === "scope" && selectedAlternative !== undefined ? (
              <>
                <Text style={styles.bodyText}>برای «{selectedAlternative.exercise.name_fa}» این تعویض تا چه زمانی باشد؟</Text>
                <ChoiceGroup
                  disabled={submitting || offline}
                  label="مدت جایگزینی"
                  options={replacementScopes}
                  selected=""
                  onSelect={(value) => void submit(value)}
                />
              </>
            ) : null}
            {error !== null ? <Notice message={error} variant="danger" /> : null}
            {offline ? <Notice message="برای ثبت جایگزین به اینترنت وصل شو." variant="offline" /> : null}
            {submitting ? <Text accessibilityLiveRegion="polite" accessibilityRole="alert" style={styles.bodyText}>در حال ثبت جایگزین…</Text> : null}
          </>
        )}
      </Card>
    </View>
  );
}

export type CompletionFeedbackControllerState =
  | "completed"
  | "draft"
  | "error"
  | "hidden"
  | "loading"
  | "offline";

export type CompletionFeedbackController = {
  readonly awaitingCoachApproval: boolean;
  readonly context: WorkoutCycleCompletionFeedback | null;
  readonly currentWeek: number | null;
  readonly durationWeeks: number;
  readonly error: string | null;
  readonly form: CompletionFeedbackForm;
  readonly lockedInfoOpen: boolean;
  readonly offline: boolean;
  readonly saving: boolean;
  readonly state: CompletionFeedbackControllerState;
  readonly retry: () => void;
  readonly submit: () => void;
  readonly toggleLockedInfo: () => void;
  readonly updateForm: <TField extends keyof CompletionFeedbackForm>(
    field: TField,
    value: CompletionFeedbackForm[TField],
  ) => void;
};

export function useCompletionFeedbackController({
  api,
  awaitingCoachApproval = false,
  connectivityStatus,
  fallbackDurationWeeks,
  planId,
}: {
  readonly api: WorkoutCycleApi;
  readonly awaitingCoachApproval?: boolean;
  readonly connectivityStatus: ConnectivityStatus;
  readonly fallbackDurationWeeks: number;
  readonly planId: string | null;
}): CompletionFeedbackController {
  const queryClient = useQueryClient();
  const cycleQuery = useQuery({
    enabled: planId !== null && !awaitingCoachApproval,
    queryFn: api.getCurrent,
    queryKey: workoutKeys.currentCycle(),
  });
  const cycleState = getMobileViewState(cycleQuery, { context: "workout", connectivityStatus });
  const queriedCycle = viewData(cycleState);
  const cycle = queriedCycle !== undefined
    && queriedCycle !== null
    && planId !== null
    && queriedCycle.workout_plan_id === planId
    ? queriedCycle
    : null;
  const feedbackKey = workoutKeys.completionFeedback(cycle?.cycle_id ?? "unavailable");
  const feedbackQuery = useQuery({
    enabled: cycle !== null && !awaitingCoachApproval,
    queryFn: api.getCompletionFeedback,
    queryKey: feedbackKey,
  });
  const feedbackState = getMobileViewState(feedbackQuery, { context: "workout", connectivityStatus });
  const queriedContext = cycle === null ? undefined : viewData(feedbackState);
  const context = queriedContext ?? null;
  const [form, setForm] = useState<CompletionFeedbackForm>(emptyCompletionFeedbackForm);
  const [error, setError] = useState<string | null>(null);
  const [lockedInfoOpen, setLockedInfoOpen] = useState(false);
  const save = useMutation({
    mutationFn: api.saveCompletionFeedback,
    onError: (requestError: unknown) => setError(mobileRequestErrorMessage(
      requestError,
      "بازخورد پایان چرخه ثبت نشد؛ دوباره تلاش کن.",
      { audience: "member", context: "workout" },
    )),
    onSuccess: (saved) => {
      queryClient.setQueryData(feedbackKey, saved);
      setError(null);
    },
  });

  useEffect(() => {
    if (queriedContext !== undefined) {
      setForm(completionFeedbackFormFromResponse(queriedContext?.feedback ?? null));
    }
  }, [queriedContext]);

  const state: CompletionFeedbackControllerState = awaitingCoachApproval
    ? "hidden"
    : cycle === null && queriedCycle === undefined
      ? cycleState.status === "offline" ? "offline" : cycleState.status === "error" ? "error" : "loading"
      : cycle !== null && queriedContext === undefined
        ? feedbackState.status === "offline" ? "offline" : feedbackState.status === "error" ? "error" : "loading"
        : context?.feedback !== null && context?.feedback !== undefined
          ? "completed"
          : context?.is_due === true
            ? "draft"
            : "hidden";

  const durationWeeks = context?.duration_weeks ?? cycle?.duration_weeks ?? fallbackDurationWeeks;
  const currentWeek = context?.current_week ?? cycle?.current_week ?? null;
  const offline = connectivityStatus === "offline";

  function retry() {
    if (cycle !== null) {
      void feedbackQuery.refetch();
      return;
    }
    void cycleQuery.refetch();
  }

  function submit() {
    if (offline) {
      setError("ثبت بازخورد بدون اینترنت انجام نمی‌شود.");
      return;
    }
    setError(null);
    save.mutate(toCompletionFeedbackInput(form));
  }

  function updateForm<TField extends keyof CompletionFeedbackForm>(
    field: TField,
    value: CompletionFeedbackForm[TField],
  ) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  const queryError = cycleState.status === "error"
    ? cycleState.error.message
    : feedbackState.status === "error"
      ? feedbackState.error.message
      : null;

  return {
    awaitingCoachApproval,
    context,
    currentWeek,
    durationWeeks,
    error: error ?? queryError,
    form,
    lockedInfoOpen,
    offline,
    retry,
    saving: save.isPending,
    state,
    submit,
    toggleLockedInfo: () => setLockedInfoOpen((open) => !open),
    updateForm,
  };
}

export function CompletionFeedbackToolCell({
  controller,
}: {
  readonly controller: CompletionFeedbackController;
}) {
  const locked = controller.state === "hidden";
  return (
    <Pressable
      accessibilityLabel="بازخورد پایان دوره"
      accessibilityRole="button"
      accessibilityState={{ expanded: locked ? controller.lockedInfoOpen : undefined }}
      onPress={locked ? controller.toggleLockedInfo : undefined}
      style={({ pressed }) => [styles.toolsCell, styles.toolsCellDivided, pressed && styles.toolPressed]}
      testID="workout-plan-feedback-tool"
    >
      <View style={styles.feedbackIconFrame}>
        <AppIcon color={fiticianTokens.colors.aqua} name="feedback" size={fiticianTokens.iconSize.md} />
        {locked ? (
          <View style={styles.lockBadge} testID="workout-plan-feedback-lock">
            <AppIcon color={fiticianTokens.colors.ink} name="lock" size={11} />
          </View>
        ) : null}
      </View>
      <Text style={styles.toolEyebrow}>پایان دوره</Text>
      <Text numberOfLines={2} style={styles.toolTitle}>بازخورد پایان دوره</Text>
    </Pressable>
  );
}

export function CompletionFeedbackDetails({
  controller,
}: {
  readonly controller: CompletionFeedbackController;
}) {
  if (controller.state === "hidden") {
    if (!controller.lockedInfoOpen) return null;
    const weeks = formatPersianNumber(controller.durationWeeks, { maximumFractionDigits: 0 });
    const message = controller.awaitingCoachApproval
      ? `این برنامه هنوز به تأیید مربی نرسیده است. پس از تأیید مربی و اتمام دوره ${weeks} هفته‌ای، این فرم برای هدفمندتر شدن برنامه بعدی فعال می‌شود. لطفاً فرم را کامل و با دقت پر کنید.`
      : `پس از اتمام دوره ${weeks} هفته‌ای، این فرم برای هدفمندتر شدن برنامه بعدی فعال می‌شود. لطفاً فرم را کامل و با دقت پر کنید.`;
    return (
      <View style={styles.feedbackDetails}>
        <Text style={styles.lockedFeedbackText}>{message}</Text>
      </View>
    );
  }

  if (controller.state === "loading") {
    return (
      <View style={styles.feedbackDetails}>
        <Skeleton height={64} />
      </View>
    );
  }
  if (controller.state === "error") {
    return (
      <View style={styles.feedbackDetails}>
        <Notice
          actionLabel="تلاش دوباره"
          message={controller.error ?? "وضعیت بازخورد پایان چرخه دریافت نشد."}
          onAction={controller.retry}
          variant="danger"
        />
      </View>
    );
  }
  if (controller.state === "offline") {
    return (
      <View style={styles.feedbackDetails}>
        <Notice message="برای دریافت بازخورد پایان چرخه به اینترنت وصل شو." variant="offline" />
      </View>
    );
  }
  if (controller.state === "completed" && controller.context?.feedback !== null && controller.context?.feedback !== undefined) {
    return (
      <View style={styles.feedbackDetails}>
        <Text style={styles.sectionTitle}>بازخورد پایان چرخه</Text>
        <Text style={styles.successText}>بازخورد این چرخه ثبت شده است.</Text>
        <Text style={styles.bodyText}>
          شدت: {difficultyLabel(controller.context.feedback.overall_difficulty ?? "appropriate")} · ریکاوری: {recoveryLabel(controller.context.feedback.overall_recovery ?? "good")}
        </Text>
      </View>
    );
  }

  const offline = controller.offline;
  const context = controller.context;
  if (context === null || context === undefined || controller.state !== "draft") return null;

  return (
    <View style={[styles.feedbackDetails, styles.formCard]}>
      <View style={styles.formHeading}>
        <View style={styles.summaryCopy}>
          <Text style={styles.sectionEyebrow}>پایان چرخه</Text>
          <Text style={styles.sectionTitle}>بازخورد کلی</Text>
        </View>
        <Text style={styles.weekBadge}>هفته {controller.currentWeek ?? context.current_week}</Text>
      </View>
      <ChoiceGroup
        label="شدت کلی تمرین‌ها"
        options={difficultyChoices}
        selected={controller.form.overallDifficulty}
        onSelect={(value) => controller.updateForm("overallDifficulty", value as CompletionFeedbackForm["overallDifficulty"])}
      />
      <ChoiceGroup
        label="ریکاوری کلی"
        options={recoveryChoices}
        selected={controller.form.overallRecovery}
        onSelect={(value) => controller.updateForm("overallRecovery", value as CompletionFeedbackForm["overallRecovery"])}
      />
      <ChoiceGroup
        label="رضایت کلی"
        options={satisfactionChoices}
        selected={controller.form.overallSatisfaction}
        onSelect={(value) => controller.updateForm("overallSatisfaction", value as CompletionFeedbackForm["overallSatisfaction"])}
      />
      <ChoiceGroup
        label="پیشرفت قدرت"
        options={progressChoices}
        selected={controller.form.strengthProgress}
        onSelect={(value) => controller.updateForm("strengthProgress", value as CompletionFeedbackForm["strengthProgress"])}
      />
      <ChoiceGroup
        label="پیشرفت عضله"
        options={progressChoices}
        selected={controller.form.muscleProgress}
        onSelect={(value) => controller.updateForm("muscleProgress", value as CompletionFeedbackForm["muscleProgress"])}
      />
      <ChoiceGroup
        label="پیشرفت استقامت"
        options={progressChoices}
        selected={controller.form.enduranceProgress}
        onSelect={(value) => controller.updateForm("enduranceProgress", value as CompletionFeedbackForm["enduranceProgress"])}
      />
      <ChoiceGroup
        label="پیشرفت انرژی"
        options={progressChoices}
        selected={controller.form.energyProgress}
        onSelect={(value) => controller.updateForm("energyProgress", value as CompletionFeedbackForm["energyProgress"])}
      />
      <TextField
        label="تغییرات عملکرد"
        maxLength={4000}
        multiline
        numberOfLines={3}
        onChangeText={(performanceChanges) => controller.updateForm("performanceChanges", performanceChanges)}
        value={controller.form.performanceChanges}
      />
      <TextField
        label="درد یا محدودیت"
        maxLength={4000}
        multiline
        numberOfLines={3}
        onChangeText={(painFeedback) => controller.updateForm("painFeedback", painFeedback)}
        value={controller.form.painFeedback}
      />
      <TextField
        label="یادداشت پایانی"
        maxLength={4000}
        multiline
        numberOfLines={3}
        onChangeText={(note) => controller.updateForm("note", note)}
        value={controller.form.note}
      />
      {controller.error !== null ? <Notice message={controller.error} variant="danger" /> : null}
      {offline ? <Notice message="برای ثبت بازخورد به اینترنت وصل شو." variant="offline" /> : null}
      <Button disabled={offline} label="ثبت بازخورد" loading={controller.saving} onPress={controller.submit} />
    </View>
  );
}

function ChoiceGroup<TValue extends string>({
  disabled = false,
  label,
  onSelect,
  options,
  selected,
}: {
  readonly disabled?: boolean;
  readonly label: string;
  readonly onSelect: (value: TValue) => void;
  readonly options: readonly Choice<TValue>[];
  readonly selected: string;
}) {
  return (
    <View style={styles.formGroup}>
      {label ? <Text style={styles.fieldLabel}>{label}</Text> : null}
      <View style={styles.choiceRow}>
        {options.map((option) => (
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={option.label}
            disabled={disabled}
            accessibilityState={{ disabled, selected: option.value === selected }}
            key={option.value}
            onPress={(event) => {
              event?.stopPropagation();
              if (!disabled) onSelect(option.value);
            }}
            style={[styles.choice, option.value === selected && styles.choiceSelected]}
          >
            <Text style={[styles.choiceText, option.value === selected && styles.choiceTextSelected]}>
              {option.label}
            </Text>
            {option.description ? <Text style={styles.bodyText}>{option.description}</Text> : null}
          </Pressable>
        ))}
      </View>
    </View>
  );
}

function viewData<TData>(state: MobileViewState<TData>): TData | undefined {
  if (state.status === "loading") return undefined;
  return "data" in state ? state.data : undefined;
}

function useConnectivityStatus(): ConnectivityStatus {
  const [status, setStatus] = useState<ConnectivityStatus>(connectivityMonitor.getSnapshot().status);
  useEffect(() => connectivityMonitor.subscribe((snapshot) => setStatus(snapshot.status)), []);
  return status;
}

function formatDate(value: string): string {
  return formatTehranDateTime(value);
}

function difficultyLabel(value: "too_easy" | "easy" | "appropriate" | "hard" | "too_hard"): string {
  return difficultyChoices.find((choice) => choice.value === value)?.label ?? value;
}

function recoveryLabel(value: "good" | "average" | "poor"): string {
  return recoveryChoices.find((choice) => choice.value === value)?.label ?? value;
}

const styles = StyleSheet.create({
  bodyText: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    lineHeight: 23,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  choice: {
    backgroundColor: fiticianTokens.colors.surfaceSubtle,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.pill,
    borderWidth: 1,
    minHeight: fiticianTokens.layout.minimumTouchTarget,
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[2],
  },
  choiceRow: {
    alignItems: "flex-start",
    flexDirection: "row",
    flexWrap: "wrap",
    gap: fiticianTokens.spacing[2],
  },
  choiceSelected: {
    backgroundColor: fiticianTokens.colors.aqua,
    borderColor: fiticianTokens.colors.aqua,
  },
  choiceText: {
    color: fiticianTokens.colors.mist,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  choiceTextSelected: {
    color: fiticianTokens.colors.canvas,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
  },
  cycleStatus: {
    color: fiticianTokens.colors.success,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  feedbackDetails: {
    borderTopColor: fiticianTokens.colors.line,
    borderTopWidth: 1,
    gap: fiticianTokens.spacing[3],
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[3],
  },
  feedbackCard: {
    gap: fiticianTokens.spacing[3],
  },
  feedbackIconFrame: {
    alignItems: "center",
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.small,
    borderWidth: 1,
    height: 34,
    justifyContent: "center",
    position: "relative",
    width: 34,
  },
  lockedFeedbackText: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    lineHeight: 20,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  lockBadge: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceRaised,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.pill,
    borderWidth: 1,
    bottom: -5,
    height: 17,
    justifyContent: "center",
    position: "absolute",
    right: -6,
    width: 17,
  },
  toolEyebrow: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: 10,
    lineHeight: 14,
    textAlign: "center",
    writingDirection: "rtl",
  },
  toolPressed: {
    opacity: 0.78,
  },
  toolTitle: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    lineHeight: 16,
    textAlign: "center",
    writingDirection: "rtl",
  },
  toolsCell: {
    alignItems: "center",
    flex: 1,
    gap: 2,
    justifyContent: "center",
    minHeight: 80,
    minWidth: 0,
    paddingHorizontal: 4,
    paddingVertical: 8,
  },
  toolsCellDivided: {
    borderRightColor: fiticianTokens.colors.line,
    borderRightWidth: 1,
  },
  formCard: {
    gap: fiticianTokens.spacing[4],
  },
  fieldLabel: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.medium,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  formGroup: {
    gap: fiticianTokens.spacing[2],
  },
  formHeading: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: fiticianTokens.spacing[3],
    justifyContent: "space-between",
  },
  panel: {
    gap: fiticianTokens.spacing[3],
    marginTop: fiticianTokens.spacing[4],
  },
  sectionEyebrow: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  sectionTitle: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h3,
    lineHeight: 28,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  successText: {
    color: fiticianTokens.colors.success,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    lineHeight: 25,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  summaryCard: {
    backgroundColor: fiticianTokens.colors.surfaceSubtle,
    borderColor: fiticianTokens.colors.line,
    borderRadius: fiticianTokens.radii.large,
    borderWidth: 1,
    elevation: fiticianTokens.shadows.soft.elevation,
    gap: fiticianTokens.spacing[3],
    padding: fiticianTokens.spacing[3],
    shadowColor: fiticianTokens.shadows.soft.color,
    shadowOffset: fiticianTokens.shadows.soft.offset,
    shadowOpacity: fiticianTokens.shadows.soft.opacity,
    shadowRadius: fiticianTokens.shadows.soft.radius,
  },
  summaryCopy: {
    flex: 1,
    gap: fiticianTokens.spacing[1],
  },
  summaryHeading: {
    alignItems: "flex-start",
    flexDirection: "row",
    gap: fiticianTokens.spacing[3],
    justifyContent: "space-between",
  },
  summaryMetric: {
    alignItems: "center",
    flex: 1,
    gap: 2,
    justifyContent: "center",
    minWidth: 0,
  },
  summaryMetricDivider: {
    backgroundColor: fiticianTokens.colors.line,
    height: "70%",
    width: 1,
  },
  summaryMetricLabel: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: 10,
    lineHeight: 14,
    textAlign: "center",
    writingDirection: "rtl",
  },
  summaryMetricValue: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: 11,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    lineHeight: 16,
    textAlign: "center",
    writingDirection: "rtl",
  },
  summaryMetricValueAqua: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyEnglish,
    fontSize: 18,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    lineHeight: 20,
    textAlign: "center",
    writingDirection: "ltr",
  },
  summaryMetrics: {
    alignItems: "stretch",
    flexDirection: "row",
    minHeight: 42,
    width: "100%",
  },
  weekBadge: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.sm,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    textAlign: "auto",
    writingDirection: "rtl",
  },
});
