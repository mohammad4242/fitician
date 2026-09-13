import { useRouter } from "expo-router";
import { StyleSheet, Text, View, useWindowDimensions } from "react-native";

import { ExerciseMedia } from "../exercises/ExerciseMedia";
import type { WorkoutDay } from "../workouts/workoutApi";
import { Button, CinematicSurface, StateSkeleton } from "../ui/components";
import { formatPersianNumber } from "../ui/locale";
import { RTL_ROW } from "../ui/rtl";
import { fiticianTokens } from "../ui/tokens";
import type { HomeWorkoutSummary } from "./homeModel";
import { getHomeHeroLayout } from "./homePresentation";

export type WorkoutHomeState = "empty" | "error" | "loading" | "locked" | "offline" | "pending" | "ready" | "stale";

export interface WorkoutTodayCardProps {
  readonly day: WorkoutDay | null;
  readonly state: WorkoutHomeState;
  readonly summary?: HomeWorkoutSummary | null;
}

export function WorkoutTodayCard({ day, state, summary }: WorkoutTodayCardProps) {
  const router = useRouter();
  const { width } = useWindowDimensions();
  const stacked = getHomeHeroLayout(width) === "stacked";
  const timelineState = summary?.state;
  const focusedSession = summary?.focusedSession ?? null;
  const nextSession = summary?.nextSession ?? null;
  const firstExercise = day?.exercises[0];
  const title = timelineState === undefined
    ? day?.title_fa || day?.title_en || "تمرین امروز"
    : focusedSession?.title_fa || focusedSession?.title_en || timelineTitle(timelineState);
  const canStart = timelineState === undefined && day !== null && state === "ready";

  if (timelineState === undefined && state === "loading" && day === null) return <StateSkeleton variant="hero" />;

  return (
    <CinematicSurface accent style={styles.card} variant="hero">
      <View style={[styles.layout, RTL_ROW, stacked && styles.layoutStacked]}>
        <View style={[styles.mediaWrap, stacked && styles.mediaStacked]}>
          {firstExercise ? (
            <ExerciseMedia
              accessibilityLabel={`رسانه تمرین ${firstExercise.exercise.name_fa || firstExercise.exercise.name_en}`}
              autoplay
              mediaType={firstExercise.exercise.media_type}
              name={firstExercise.exercise.name_fa || firstExercise.exercise.name_en}
              path={firstExercise.exercise.media_path}
              style={styles.media}
            />
          ) : (
            <View style={styles.emptyMedia}>
              <Text style={styles.emptyMediaText}>{emptyMediaMessage(timelineState, state)}</Text>
            </View>
          )}
          <View pointerEvents="none" style={styles.mediaScrim} />
        </View>

        <View style={styles.copy}>
          <View style={styles.topLine}>
            <View style={styles.statusPill}>
              <View style={styles.statusDot} />
              <Text style={styles.statusText}>{timelineState === undefined ? stateLabel(state, Boolean(day)) : timelineStateLabel(timelineState)}</Text>
            </View>
            <Text style={styles.eyebrow}>تمرین امروز</Text>
          </View>
          <Text numberOfLines={3} style={styles.title}>{title}</Text>
          <View style={styles.dayLine}>
            <View style={styles.dayBadge}>
              <Text style={styles.dayNumber}>{focusedSession
                ? formatPersianNumber(focusedSession.session_number, { maximumFractionDigits: 0, useGrouping: false }).padStart(2, "۰")
                : day
                  ? formatPersianNumber(day.day_number, { maximumFractionDigits: 0, useGrouping: false }).padStart(2, "۰")
                  : "—"}</Text>
            </View>
            <View style={styles.sessionFacts}>
              <Text style={styles.factValue}>{focusedSession
                ? `جلسه ${formatPersianNumber(focusedSession.session_number)} · هفته ${formatPersianNumber(focusedSession.week_number)}`
                : day
                  ? `${formatPersianNumber(day.estimated_duration_minutes, { maximumFractionDigits: 0 })} دقیقه`
                  : nextSession
                    ? `تمرین بعدی: ${nextSession.scheduled_date}`
                    : "—"}</Text>
            </View>
          </View>
          {timelineState === "overdue" && focusedSession ? (
            <Text style={styles.stateText}>
              جلسه {formatPersianNumber(focusedSession.session_number)} عقب افتاده است · برنامه‌ریزی‌شده برای {focusedSession.scheduled_date}
            </Text>
          ) : null}
          {timelineState === "rest" && nextSession ? (
            <Text style={styles.stateText}>
              تمرین بعدی: {nextSession.scheduled_date} · جلسه {formatPersianNumber(nextSession.session_number)}
            </Text>
          ) : null}
          {timelineState === "completed" ? (
            <Text style={styles.stateText}>
              تمرین امروز کامل شد{nextSession ? ` · بعدی: ${nextSession.scheduled_date}` : ""}
            </Text>
          ) : null}
          {timelineState === "legacy" ? (
            <Text style={styles.stateText}>اطلاعات دقیق جلسه‌های روزانه برای این برنامه قدیمی در دسترس نیست.</Text>
          ) : null}
          {timelineState === "ready" ? (
            <Text style={styles.stateText}>تاریخ شروع را از بخش تمرین انتخاب کن.</Text>
          ) : null}
          {timelineState === "scheduled" ? (
            <Text style={styles.stateText}>با رسیدن تاریخ شروع، جلسه‌های برنامه نمایش داده می‌شوند.</Text>
          ) : null}
          {timelineState === undefined && state === "error" ? (
            <Text style={styles.stateText}>دریافت برنامه انجام نشد؛ از بخش تمرین دوباره تلاش کن.</Text>
          ) : null}
          {timelineState === undefined && state === "locked" ? (
            <Text style={styles.stateText}>برنامه‌ای وجود ندارد؛ ساخت برنامه با دسترسی فعلی ممکن نیست.</Text>
          ) : null}
          <Button
            label={timelineState === "ready" ? "شروع برنامه" : canStart ? "شروع تمرین" : state === "locked" ? "مشاهده وضعیت دسترسی" : "مشاهده برنامه"}
            onPress={() => router.push("/member/workouts")}
            style={styles.action}
          />
        </View>
      </View>
    </CinematicSurface>
  );
}

function emptyMediaMessage(timelineState: HomeWorkoutSummary["state"] | undefined, state: WorkoutHomeState): string {
  if (timelineState === "ready") return "برنامه آماده است؛ تاریخ شروع را انتخاب کن.";
  if (timelineState === "rest") return "امروز روز استراحت است.";
  if (timelineState === "legacy") return "جزئیات دقیق جلسه‌های این برنامه قدیمی در دسترس نیست.";
  if (state === "locked") return "برای ساخت برنامه تمرینی، دسترسی فعال لازم است.";
  return "جلسه بعدی پس از آماده‌شدن برنامه اینجا دیده می‌شود.";
}

function timelineStateLabel(state: HomeWorkoutSummary["state"]): string {
  if (state === "ready") return "آماده شروع";
  if (state === "scheduled") return "شروع زمان‌بندی‌شده";
  if (state === "today") return "تمرین امروز";
  if (state === "overdue") return "جلسه عقب‌افتاده";
  if (state === "rest") return "روز استراحت";
  if (state === "completed") return "کامل‌شده امروز";
  if (state === "legacy") return "برنامه فعال";
  return "بدون برنامه";
}

function timelineTitle(state: HomeWorkoutSummary["state"]): string {
  if (state === "ready") return "برنامه آماده شروع است";
  if (state === "scheduled") return "شروع برنامه زمان‌بندی شده است";
  if (state === "rest") return "روز استراحت";
  if (state === "legacy") return "برنامه تمرینی";
  if (state === "completed") return "تمرین امروز کامل شد";
  return "تمرین امروز";
}

function stateLabel(state: WorkoutHomeState, hasDay: boolean): string {
  if (state === "pending") return "در انتظار تأیید";
  if (state === "locked") return "دسترسی لازم است";
  if (state === "offline") return "آفلاین";
  if (state === "stale") return "ذخیره‌شده";
  if (state === "error") return "خطا";
  if (!hasDay) return "بدون برنامه";
  return "برنامه فعال";
}

const styles = StyleSheet.create({
  action: {
    alignSelf: "stretch",
    marginTop: "auto",
    paddingHorizontal: fiticianTokens.spacing[3],
    paddingVertical: fiticianTokens.spacing[2],
  },
  card: { minHeight: 204, width: "100%" },
  copy: { flex: 1.05, gap: fiticianTokens.spacing[2], padding: fiticianTokens.spacing[3] },
  dayBadge: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceInteractive,
    borderColor: fiticianTokens.colors.lineStrong,
    borderRadius: fiticianTokens.radii.medium,
    borderWidth: 1,
    height: 44,
    justifyContent: "center",
    width: 44,
  },
  dayLine: { alignItems: "center", flexDirection: "row", gap: fiticianTokens.spacing[2] },
  dayNumber: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyEnglish,
    fontSize: fiticianTokens.typography.fontSize.h3,
    fontWeight: fiticianTokens.typography.fontWeight.extraBold,
    writingDirection: "ltr",
  },
  emptyMedia: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.petrol,
    flex: 1,
    gap: fiticianTokens.spacing[2],
    justifyContent: "center",
    padding: fiticianTokens.spacing[4],
  },
  emptyMediaText: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    lineHeight: 19,
    textAlign: "center",
    writingDirection: "rtl",
  },
  eyebrow: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  factValue: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  layout: { flexDirection: "row", minHeight: 204 },
  layoutStacked: { flexDirection: "column" },
  media: { borderRadius: 0, flex: 1, minHeight: 204 },
  mediaScrim: {
    backgroundColor: fiticianTokens.colors.scrim,
    bottom: 0,
    left: 0,
    position: "absolute",
    right: 0,
    top: "54%",
  },
  mediaStacked: { flex: 0, height: 120, minHeight: 120 },
  mediaWrap: {
    backgroundColor: fiticianTokens.colors.surfaceRaised,
    flex: 1.15,
    minHeight: 204,
    overflow: "hidden",
    position: "relative",
  },
  sessionFacts: { flex: 1 },
  stateText: {
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: 10,
    lineHeight: 17,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  statusDot: {
    backgroundColor: fiticianTokens.colors.aqua,
    borderRadius: fiticianTokens.radii.pill,
    height: 5,
    width: 5,
  },
  statusPill: {
    alignItems: "center",
    backgroundColor: fiticianTokens.colors.surfaceInteractive,
    borderRadius: fiticianTokens.radii.pill,
    flexDirection: "row",
    gap: 5,
    paddingHorizontal: fiticianTokens.spacing[2],
    paddingVertical: 5,
  },
  statusText: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: 9,
    textAlign: "center",
    writingDirection: "rtl",
  },
  title: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h2,
    lineHeight: 31,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  topLine: {
    alignItems: "center",
    flexDirection: "row",
    gap: fiticianTokens.spacing[2],
    justifyContent: "space-between",
  },
});
