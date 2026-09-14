import { useQuery } from "@tanstack/react-query";
import { localIsoDate, resolvedIanaTimeZone } from "@fitician/core";
import type { TimelineWorkout } from "@fitician/core/program-timeline";
import { useRouter } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { Pressable, StyleSheet, Text, View, useWindowDimensions } from "react-native";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { nutritionKeys, profileKeys, programTimelineKeys, workoutKeys } from "../data/queryKeys";
import { useMobileEntitlements } from "../entitlements/EntitlementProvider";
import { BodyAnalysisAccessNotice } from "../bodyAnalysis/BodyAnalysisAccessNotice";
import { resolveBodyAnalysisAccessState } from "../bodyAnalysis/bodyAnalysisAccess";
import { connectivityMonitor, type ConnectivityStatus } from "../platform/connectivity";
import { createProfileApi } from "../profile/profileApi";
import { createNutritionApi } from "../nutrition/nutritionApi";
import { createNutritionPlanApi } from "../nutrition/nutritionPlanApi";
import { createNutritionTrackingApi } from "../nutrition/nutritionTrackingApi";
import { createProgramTimelineApi } from "../programTimeline/programTimelineApi";
import { createWorkoutPlanApi } from "../workouts/workoutApi";
import { findPendingWorkoutPlanId } from "../workouts/workoutModel";
import { getMobileViewState, mobileRequestErrorMessage, type MobileViewState } from "../ui/requestState";
import { Notice, PageHeading } from "../ui/components";
import { Screen } from "../ui/layout";
import { fiticianTokens } from "../ui/tokens";
import { useMobileRouteSnapshot } from "../ui/navigation/RouteGuards";
import { NutritionSummaryCard } from "./NutritionSummaryCard";
import { QuickActionCard } from "./QuickActionCard";
import { homeWorkoutSummary, nutritionSummary } from "./homeModel";
import { getQuickActionColumns } from "./homePresentation";
import { WorkoutTodayCard, type WorkoutHomeState } from "./WorkoutTodayCard";

const homeBodyImage = require("../assets/home-body.webp") as number;
const homeFoodImage = require("../assets/home-food.webp") as number;

export function MemberHomeScreen() {
  const auth = useMobileAuth();
  const entitlements = useMobileEntitlements();
  const { width } = useWindowDimensions();
  const router = useRouter();
  const snapshot = useMobileRouteSnapshot();
  const connectivityStatus = useConnectivityStatus();
  const profileApi = useMemo(() => createProfileApi(auth.request), [auth.request]);
  const workoutApi = useMemo(
    () => createWorkoutPlanApi(auth.request, auth.download),
    [auth.download, auth.request],
  );
  const nutritionApi = useMemo(() => createNutritionApi(auth.request), [auth.request]);
  const nutritionPlanApi = useMemo(
    () => createNutritionPlanApi(auth.request, auth.download),
    [auth.download, auth.request],
  );
  const nutritionTrackingApi = useMemo(
    () => createNutritionTrackingApi(auth.request, auth.download),
    [auth.download, auth.request],
  );
  const timelineApi = useMemo(() => createProgramTimelineApi(auth.request), [auth.request]);
  const deviceTimezone = useMemo(resolvedIanaTimeZone, []);
  const productMode = snapshot.profile.productMode;
  const hasTraining = productMode === null || productMode === "training" || productMode === "both";
  const hasNutrition = productMode === "nutrition" || productMode === "both";
  const entitlementStateReady = entitlements.snapshot !== null && !entitlements.loading;
  const canGenerateWorkout = entitlementStateReady && entitlements.hasEntitlement("training.plan.generate");
  const bodyAnalysisAccessState = resolveBodyAnalysisAccessState(
    entitlements.loading || (entitlements.snapshot === null && entitlements.error === null),
    entitlementStateReady && entitlements.hasEntitlement("body_analysis.run"),
    entitlements.quotaFor("body_analysis.run"),
  );
  const sharedProfileQuery = useQuery({
    enabled: auth.status === "signed_in",
    queryFn: profileApi.getSharedProfile,
    queryKey: profileKeys.current(),
  });
  const activeWorkoutQuery = useQuery({
    enabled: hasTraining,
    queryFn: workoutApi.getActive,
    queryKey: workoutKeys.plan("active"),
  });
  const shouldLoadWorkoutHistory = hasTraining && activeWorkoutQuery.data === null;
  const workoutHistoryQuery = useQuery({
    enabled: shouldLoadWorkoutHistory,
    queryFn: workoutApi.getHistory,
    queryKey: workoutKeys.plans(),
  });
  const pendingWorkoutPlanId = findPendingWorkoutPlanId(workoutHistoryQuery.data ?? []);
  const shouldLoadPendingWorkout = activeWorkoutQuery.data === null && pendingWorkoutPlanId !== null;
  const pendingWorkoutQuery = useQuery({
    enabled: shouldLoadPendingWorkout,
    queryFn: () => workoutApi.get(pendingWorkoutPlanId as string),
    queryKey: workoutKeys.plan(pendingWorkoutPlanId ?? "pending"),
  });
  const nutritionPlanQuery = useQuery({
    enabled: hasNutrition,
    queryFn: nutritionPlanApi.getLatest,
    queryKey: nutritionKeys.plan("latest"),
  });
  const nutritionEstimateQuery = useQuery({
    enabled: hasNutrition,
    queryFn: nutritionApi.getCurrentEstimate,
    queryKey: nutritionKeys.estimate(),
  });
  const timelineQuery = useQuery({
    enabled: hasTraining || hasNutrition,
    queryFn: () => timelineApi.getToday(deviceTimezone),
    queryKey: programTimelineKeys.today(deviceTimezone),
  });
  const today = timelineQuery.data?.local_date ?? localIsoDate();
  const trackingQuery = useQuery({
    enabled: hasNutrition,
    queryFn: () => nutritionTrackingApi.getDailyTracking(today),
    queryKey: nutritionKeys.tracking(today),
  });

  const sharedProfileState = getMobileViewState(sharedProfileQuery, {
    audience: "member",
    connectivityStatus,
    context: "profile",
    isEmpty: (data) => data === null,
  });
  const activeWorkoutState = getMobileViewState(activeWorkoutQuery, {
    audience: "member",
    connectivityStatus,
    context: "workout",
    isEmpty: (data) => data === null,
  });
  const nutritionPlanState = getMobileViewState(nutritionPlanQuery, {
    audience: "member",
    connectivityStatus,
    context: "nutrition",
    isEmpty: (data) => data === null,
  });
  const nutritionEstimateState = getMobileViewState(nutritionEstimateQuery, {
    audience: "member",
    connectivityStatus,
    context: "nutrition",
    isEmpty: (data) => data === null,
  });
  const trackingState = getMobileViewState(trackingQuery, {
    audience: "member",
    connectivityStatus,
    context: "nutrition",
  });
  const activeWorkoutPlan = viewData(activeWorkoutState);
  const pendingWorkoutPlan = shouldLoadPendingWorkout
    && pendingWorkoutQuery.data?.status === "pending_review"
    ? pendingWorkoutQuery.data
    : undefined;
  const workoutPlan = activeWorkoutPlan ?? pendingWorkoutPlan;
  const nutritionPlan = viewData(nutritionPlanState);
  const nutritionEstimate = viewData(nutritionEstimateState);
  const tracking = viewData(trackingState);
  const timeline = timelineQuery.data ?? null;
  const timelineWorkout: TimelineWorkout | null = timeline?.workout ?? null;
  const liveWorkoutSummary = timelineWorkout?.state === "no_plan"
    ? null
    : timelineWorkout === null
      ? null
      : homeWorkoutSummary(timelineWorkout);
  const focusedWorkoutDay = liveWorkoutSummary?.focusedSession !== null
    && liveWorkoutSummary?.focusedSession !== undefined
    ? workoutPlan?.days.find((day) => day.id === liveWorkoutSummary.focusedSession?.workout_day_id) ?? null
    : pendingWorkoutPlan?.days.at(0) ?? null;
  const nutritionDataLoading = hasNutrition && (
    nutritionPlanState.status === "loading"
    || nutritionEstimateState.status === "loading"
    || trackingState.status === "loading"
  );
  const nutritionHasError = [nutritionPlanState, nutritionEstimateState, trackingState]
    .some((state) => state.status === "error");
  const nutritionErrorMessage = [nutritionPlanState, nutritionEstimateState, trackingState]
    .find((state) => state.status === "error");
  const summary = nutritionSummary(nutritionPlan, nutritionEstimate, tracking, today, timeline?.nutrition);
  const waitingForPendingWorkout = activeWorkoutState.status === "empty" && (
    workoutHistoryQuery.isPending
    || (pendingWorkoutPlanId !== null && pendingWorkoutQuery.isPending)
  );
  const pendingWorkoutFailed = activeWorkoutState.status === "empty"
    && pendingWorkoutPlan === undefined
    && (
      workoutHistoryQuery.isError
      || (pendingWorkoutPlanId !== null && pendingWorkoutQuery.isError)
    );
  const workoutErrorMessage = activeWorkoutState.status === "error"
    ? activeWorkoutState.error.message
    : pendingWorkoutQuery.isError
      ? mobileRequestErrorMessage(
        pendingWorkoutQuery.error,
        "دریافت برنامه تمرینی انجام نشد.",
        { audience: "member", context: "workout" },
      )
      : workoutHistoryQuery.isError
        ? mobileRequestErrorMessage(
          workoutHistoryQuery.error,
          "دریافت برنامه تمرینی انجام نشد.",
          { audience: "member", context: "workout" },
        )
        : null;
  const resolvedWorkoutState: WorkoutHomeState = pendingWorkoutPlan !== undefined
    ? "pending"
    : waitingForPendingWorkout
      ? "loading"
      : pendingWorkoutFailed
        ? "error"
        : resolveWorkoutState(activeWorkoutState);
  const workoutState: WorkoutHomeState = entitlementStateReady
    && !canGenerateWorkout
    && resolvedWorkoutState === "empty"
    ? "locked"
    : resolvedWorkoutState;
  const displayName = sharedProfileQuery.data?.display_name?.trim()
    || snapshot.session.user?.email?.split("@", 1)[0]
    || "دوست";
  const avatar = displayName.slice(0, 1).toLocaleUpperCase("fa-IR");

  return (
    <Screen contentWidth="reading" contentContainerStyle={styles.screen}>
      <PageHeading
        action={<Pressable
          accessibilityLabel="باز کردن پروفایل"
          accessibilityRole="button"
          onPress={() => router.push("/member/profile")}
          style={({ pressed }) => [styles.avatar, pressed && styles.pressed]}
        >
          <Text style={styles.avatarText}>{avatar}</Text>
        </Pressable>}
        supportingText="برای امروز آماده‌ای؟"
        title={`سلام، ${displayName}`}
      />

      {sharedProfileState.status === "error" ? (
        <Notice message={sharedProfileState.error.message} variant="info" />
      ) : null}

      {hasTraining ? (
        <View style={styles.section}>
          <WorkoutTodayCard
            day={focusedWorkoutDay}
            errorMessage={workoutErrorMessage ?? undefined}
            state={workoutState}
            summary={liveWorkoutSummary}
          />
        </View>
      ) : null}

      {hasNutrition ? (
        <View style={styles.section}>
          <NutritionSummaryCard
            error={nutritionHasError}
            errorMessage={nutritionErrorMessage?.status === "error" ? nutritionErrorMessage.error.message : undefined}
            loading={nutritionDataLoading}
            summary={summary}
            timeline={timeline?.nutrition}
          />
        </View>
      ) : null}

      <View style={[styles.quickGrid, getQuickActionColumns(width) === 1 && styles.quickGridStacked]}>
        <QuickActionCard
          disabled={bodyAnalysisAccessState !== "allowed"}
          icon="bodyAnalysis"
          image={homeBodyImage}
          onPress={() => router.push({
            pathname: "/member/body-analysis-capture",
            params: { fresh: "1" },
          })}
          subtitle="پیشرفت بدنت را بهتر بشناس"
          title="تحلیل بدن"
        />
        {hasNutrition ? (
          <QuickActionCard
            icon="foodLog"
            image={homeFoodImage}
            onPress={() => router.push("/member/nutrition-tracking")}
            subtitle="وعده امروزت را ثبت کن"
            title="ثبت غذا"
          />
        ) : null}
      </View>

      <BodyAnalysisAccessNotice
        quota={entitlements.quotaFor("body_analysis.run")}
        state={bodyAnalysisAccessState}
      />

      {hasTraining && workoutState === "error" ? (
        <Text style={styles.supportingText}>برای تلاش دوباره، بخش تمرین را باز کن.</Text>
      ) : null}
      {hasTraining && workoutState === "offline" ? (
        <Text style={styles.offlineText}>اتصال اینترنت برقرار نیست؛ داده‌های ذخیره‌شده را می‌بینی.</Text>
      ) : null}
    </Screen>
  );
}

function resolveWorkoutState(state: MobileViewState<Awaited<ReturnType<ReturnType<typeof createWorkoutPlanApi>["getActive"]>>>): WorkoutHomeState {
  if (state.status === "loading") return "loading";
  if (state.status === "error") return "error";
  if (state.status === "offline") return "offline";
  if (state.status === "stale") return "stale";
  if (state.status === "empty") return "empty";
  return "ready";
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

const styles = StyleSheet.create({
  avatar: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.aqua,
    borderRadius: fiticianTokens.radii.pill,
    height: fiticianTokens.layout.minimumTouchTarget,
    justifyContent: "center",
    width: fiticianTokens.layout.minimumTouchTarget,
  },
  avatarText: {
    color: fiticianTokens.colors.canvas,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    textAlign: "center",
    writingDirection: "rtl",
  },
  offlineText: {
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    lineHeight: 20,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  pressed: {
    opacity: 0.82,
    transform: [{ scale: fiticianTokens.motion.pressedScale }],
  },
  quickGrid: {
    flexDirection: "row",
    gap: fiticianTokens.spacing[3],
  },
  quickGridStacked: {
    flexDirection: "column",
  },
  screen: {
    gap: fiticianTokens.spacing[4],
    paddingBottom: fiticianTokens.spacing[7],
    paddingTop: fiticianTokens.spacing[3],
  },
  section: {
    gap: fiticianTokens.spacing[3],
  },
  supportingText: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    textAlign: "auto",
    writingDirection: "rtl",
  },
});
