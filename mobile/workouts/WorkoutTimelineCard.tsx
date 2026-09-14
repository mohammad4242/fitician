import { formatPersianDateWithWeekday } from "@fitician/core";
import type { TimelineWorkout } from "@fitician/core/program-timeline";
import { StyleSheet, Text, View } from "react-native";

import { Button, Card, Notice, TextField } from "../ui/components";
import { formatPersianNumber } from "../ui/locale";
import { fiticianTokens } from "../ui/tokens";
import { workoutTimelinePresentation } from "./workoutCycleModel";

export interface WorkoutTimelineCardProps {
  readonly actionError: string | null;
  readonly actionPending: boolean;
  readonly cycleStartError: string | null;
  readonly cycleStartPending: boolean;
  readonly durationWeeks: number;
  readonly rescheduleDate: string;
  readonly startDate: string;
  readonly timeline: TimelineWorkout;
  readonly onChangeRescheduleDate: (value: string) => void;
  readonly onChangeStartDate: (value: string) => void;
  readonly onCompleteSession: (sessionId: string) => void;
  readonly onRescheduleSession: (sessionId: string, scheduledDate: string) => void;
  readonly onSkipSession: (sessionId: string) => void;
  readonly onStart: () => void;
}

export function WorkoutTimelineCard({
  actionError,
  actionPending,
  cycleStartError,
  cycleStartPending,
  durationWeeks,
  rescheduleDate,
  startDate,
  timeline,
  onChangeRescheduleDate,
  onChangeStartDate,
  onCompleteSession,
  onRescheduleSession,
  onSkipSession,
  onStart,
}: WorkoutTimelineCardProps) {
  const presentation = workoutTimelinePresentation(timeline);
  const session = presentation.focusedSession;
  const startDateLabel = formatWorkoutDate(startDate);
  const scheduledStartDateLabel = timeline.start_date === null || timeline.start_date === undefined
    ? null
    : formatWorkoutDate(timeline.start_date);

  if (presentation.state === "none") return null;

  return (
    <Card style={styles.card} testID="workout-timeline-card">
      {presentation.state === "ready" ? (
        <>
          <Text style={styles.eyebrow}>برنامه تمرینی</Text>
          <Text style={styles.title}>برنامه آماده شروع است</Text>
          <TextField
            accessibilityLabel="تاریخ شروع برنامه"
            label="تاریخ شروع"
            onChangeText={onChangeStartDate}
            textDirection="ltr"
            value={startDate}
          />
          {startDateLabel !== null ? <Text style={styles.body}>تاریخ شروع: {startDateLabel}</Text> : null}
          {cycleStartError !== null ? <Notice message={cycleStartError} variant="danger" /> : null}
          <Button
            disabled={cycleStartPending}
            label="شروع برنامه"
            loading={cycleStartPending}
            onPress={onStart}
          />
        </>
      ) : null}

      {presentation.state === "scheduled" ? (
        <>
          <Text style={styles.eyebrow}>برنامه تمرینی</Text>
          <Text style={styles.title}>شروع برنامه زمان‌بندی شده است</Text>
          {scheduledStartDateLabel !== null ? <Text style={styles.body}>تاریخ شروع: {scheduledStartDateLabel}</Text> : null}
          <Text style={styles.body}>با رسیدن تاریخ شروع، وضعیت جلسه‌های برنامه نمایش داده می‌شود.</Text>
        </>
      ) : null}

      {presentation.state === "today" && session !== null ? (
        <SessionContent
          actionError={actionError}
          actionPending={actionPending}
          durationWeeks={durationWeeks}
          kind="today"
          rescheduleDate={rescheduleDate}
          session={session}
          onChangeRescheduleDate={onChangeRescheduleDate}
          onCompleteSession={onCompleteSession}
          onRescheduleSession={onRescheduleSession}
          onSkipSession={onSkipSession}
        />
      ) : null}

      {presentation.state === "overdue" && session !== null ? (
        <SessionContent
          actionError={actionError}
          actionPending={actionPending}
          durationWeeks={durationWeeks}
          kind="overdue"
          rescheduleDate={rescheduleDate}
          session={session}
          onChangeRescheduleDate={onChangeRescheduleDate}
          onCompleteSession={onCompleteSession}
          onRescheduleSession={onRescheduleSession}
          onSkipSession={onSkipSession}
        />
      ) : null}

      {presentation.state === "rest" ? (
        <>
          <Text style={styles.eyebrow}>برنامه تمرینی</Text>
          <Text style={styles.title}>روز استراحت</Text>
          {presentation.nextSession !== null ? (
            <Text style={styles.body}>
              تمرین بعدی · جلسه {formatPersianNumber(presentation.nextSession.session_number, { maximumFractionDigits: 0 })}
              {" · "}{formatWorkoutDate(presentation.nextSession.scheduled_date) ?? "تاریخ نامعتبر"}
            </Text>
          ) : <Text style={styles.body}>جلسهٔ دیگری برای این برنامه باقی نمانده است.</Text>}
        </>
      ) : null}

      {presentation.state === "completed" ? (
        <>
          <Text style={styles.eyebrow}>برنامه تمرینی</Text>
          <Text style={styles.title}>تمرین امروز کامل شد</Text>
          {presentation.nextSession !== null ? (
            <Text style={styles.body}>
              تمرین بعدی · جلسه {formatPersianNumber(presentation.nextSession.session_number, { maximumFractionDigits: 0 })}
              {" · "}{formatWorkoutDate(presentation.nextSession.scheduled_date) ?? "تاریخ نامعتبر"}
            </Text>
          ) : <Text style={styles.body}>همهٔ جلسه‌های این برنامه کامل شده‌اند.</Text>}
        </>
      ) : null}

      {presentation.state === "legacy" ? (
        <>
          <Text style={styles.eyebrow}>برنامه تمرینی</Text>
          <Text style={styles.title}>برنامه فعلی</Text>
          <Text style={styles.body}>جزئیات روزانهٔ این برنامهٔ قدیمی در دسترس نیست، اما خلاصهٔ هفتگی همچنان فعال است.</Text>
        </>
      ) : null}
    </Card>
  );
}

function SessionContent({
  actionError,
  actionPending,
  durationWeeks,
  kind,
  rescheduleDate,
  session,
  onChangeRescheduleDate,
  onCompleteSession,
  onRescheduleSession,
  onSkipSession,
}: {
  readonly actionError: string | null;
  readonly actionPending: boolean;
  readonly durationWeeks: number;
  readonly kind: "overdue" | "today";
  readonly rescheduleDate: string;
  readonly session: NonNullable<ReturnType<typeof workoutTimelinePresentation>["focusedSession"]>;
  readonly onChangeRescheduleDate: (value: string) => void;
  readonly onCompleteSession: (sessionId: string) => void;
  readonly onRescheduleSession: (sessionId: string, scheduledDate: string) => void;
  readonly onSkipSession: (sessionId: string) => void;
}) {
  return (
    <>
      <Text style={styles.eyebrow}>هفته {formatPersianNumber(session.week_number, { maximumFractionDigits: 0 })} از {formatPersianNumber(durationWeeks, { maximumFractionDigits: 0 })}</Text>
      <Text style={styles.title}>{kind === "overdue" ? "این جلسه عقب افتاده است" : "تمرین امروز"}</Text>
      <Text style={styles.body}>
        جلسه {formatPersianNumber(session.session_number, { maximumFractionDigits: 0 })} · {session.title_fa || session.title_en}
      </Text>
      {kind === "overdue" ? (
        <Text style={styles.warning}>زمان‌بندی اولیه: {formatWorkoutDate(session.scheduled_date) ?? "تاریخ نامعتبر"}</Text>
      ) : null}
      <View style={styles.actions}>
        {kind === "overdue" ? (
          <Button
            disabled={actionPending}
            label="انجام امروز"
            loading={actionPending}
            onPress={() => onRescheduleSession(session.id, rescheduleDate)}
          />
        ) : (
          <Button
            disabled={actionPending}
            label="تکمیل جلسه"
            loading={actionPending}
            onPress={() => onCompleteSession(session.id)}
          />
        )}
        <TextField
          accessibilityLabel="تاریخ جدید جلسه"
          label="تاریخ جدید"
          onChangeText={onChangeRescheduleDate}
          textDirection="ltr"
          value={rescheduleDate}
        />
        {formatWorkoutDate(rescheduleDate) !== null ? (
          <Text style={styles.body}>تاریخ جدید: {formatWorkoutDate(rescheduleDate)}</Text>
        ) : null}
        <Button
          disabled={actionPending}
          label="جابجایی جلسه"
          onPress={() => onRescheduleSession(session.id, rescheduleDate)}
          variant="secondary"
        />
        <Button
          disabled={actionPending}
          label="رد کردن جلسه"
          onPress={() => onSkipSession(session.id)}
          variant="ghost"
        />
      </View>
      {actionError !== null ? <Notice message={actionError} variant="danger" /> : null}
    </>
  );
}

function formatWorkoutDate(value: string): string | null {
  try {
    return formatPersianDateWithWeekday(value);
  } catch {
    return null;
  }
}

const styles = StyleSheet.create({
  actions: {
    gap: fiticianTokens.spacing[2],
  },
  body: {
    color: fiticianTokens.colors.muted,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.body,
    lineHeight: 22,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  card: {
    borderColor: fiticianTokens.colors.lineStrong,
    gap: fiticianTokens.spacing[2],
  },
  eyebrow: {
    color: fiticianTokens.colors.aqua,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.xs,
    fontWeight: fiticianTokens.typography.fontWeight.bold,
    lineHeight: 18,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  title: {
    color: fiticianTokens.colors.ink,
    fontFamily: fiticianTokens.typography.fontFamily.displayPersian,
    fontSize: fiticianTokens.typography.fontSize.h3,
    lineHeight: 28,
    textAlign: "auto",
    writingDirection: "rtl",
  },
  warning: {
    color: fiticianTokens.colors.amber,
    fontFamily: fiticianTokens.typography.fontFamily.bodyPersian,
    fontSize: fiticianTokens.typography.fontSize.compact,
    lineHeight: 20,
    textAlign: "auto",
    writingDirection: "rtl",
  },
});
