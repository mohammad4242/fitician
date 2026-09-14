import type { PrescriptionMode } from "./exercises.js";
import type { components } from "./generated/api.js";
import { IRAN_TIME_ZONE } from "./iran-calendar.js";
import type { WorkoutPlan } from "./workouts.js";

export type WorkoutReviewStatus = "pending" | "claimed" | "approved" | "rejected" | "superseded";
export type WorkoutReviewQueueView = "pending" | "mine" | "approved";
export type WorkoutReviewQueueTimestamp = "created_at" | "approved_at";
export type ReviewProfileSummary = components["schemas"]["ReviewProfileSummary"];

export type WorkoutReviewExerciseDraft = {
  order_index: number;
  exercise_id: string;
  sets: number;
  prescription_mode?: PrescriptionMode;
  reps_min: number | null;
  reps_max: number | null;
  duration_min_seconds?: number | null;
  duration_max_seconds?: number | null;
  rir: number | null;
  rest_seconds: number;
  notes_en: string | null;
  notes_fa: string | null;
};

export type WorkoutReviewDayDraft = {
  day_number: number;
  exercises: WorkoutReviewExerciseDraft[];
};

export type WorkoutReviewDraftUpdate = {
  expected_revision: number;
  coach_note: string | null;
  days: WorkoutReviewDayDraft[];
};

export type WorkoutReviewQueueItem = {
  id: string;
  source_plan_id: string;
  user_id: string;
  member_display_name: string | null;
  member_profile_photo_url?: string | null;
  fitness_goal: string | null;
  experience_level: string | null;
  status: WorkoutReviewStatus;
  claimed_by_user_id: string | null;
  lease_expires_at: string | null;
  draft_revision: number;
  created_at: string;
  approved_at: string | null;
};

export type RecencyQueueGroup<T> =
  | {
      kind: "day";
      key: string;
      date: string;
      items: T[];
    }
  | {
      kind: "week";
      key: string;
      weekOffset: number;
      startDate: string;
      endDate: string;
      items: T[];
    };

export type WorkoutReviewQueueGroup = RecencyQueueGroup<WorkoutReviewQueueItem>;

const REVIEW_DAY_MS = 24 * 60 * 60 * 1000;
const TEHRAN_DATE_PARTS_FORMATTER = new Intl.DateTimeFormat("en-US", {
  day: "2-digit",
  month: "2-digit",
  timeZone: IRAN_TIME_ZONE,
  year: "numeric",
});

function dateKeyParts(value: string): { year: number; month: number; day: number } {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new RangeError("Expected a valid ISO timestamp");
  const parts = Object.fromEntries(
    TEHRAN_DATE_PARTS_FORMATTER
      .formatToParts(date)
      .filter((part) => ["year", "month", "day"].includes(part.type))
      .map((part) => [part.type, Number(part.value)]),
  );
  return {
    day: parts.day as number,
    month: parts.month as number,
    year: parts.year as number,
  };
}

function dateKey(value: string): string {
  const parts = dateKeyParts(value);
  return `${String(parts.year).padStart(4, "0")}-${String(parts.month).padStart(2, "0")}-${String(parts.day).padStart(2, "0")}`;
}

function dateKeyToMilliseconds(value: string): number {
  return Date.parse(`${value}T00:00:00.000Z`);
}

function addDays(value: string, days: number): string {
  const date = new Date(dateKeyToMilliseconds(value));
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function ageInDays(timestamp: string, now: string): number {
  return Math.floor((dateKeyToMilliseconds(dateKey(now)) - dateKeyToMilliseconds(dateKey(timestamp))) / REVIEW_DAY_MS);
}

function weeklyGroup<T>(
  weekOffset: number,
  today: string,
  items: T[],
): RecencyQueueGroup<T> {
  const newestAge = weekOffset * 7;
  const endAge = weekOffset === 0 ? 1 : newestAge;
  return {
    endDate: addDays(today, -endAge),
    items,
    key: `week-${weekOffset}`,
    kind: "week",
    startDate: addDays(today, -(weekOffset === 0 ? 6 : newestAge + 6)),
    weekOffset,
  };
}

export function groupReviewQueueByRecency<T>(
  items: readonly T[],
  getTimestamp: (item: T) => string,
  now: string = new Date().toISOString(),
  getTieBreaker?: (item: T) => string,
): RecencyQueueGroup<T>[] {
  const sorted = [...items].sort((left, right) => {
    const timestampDifference = Date.parse(getTimestamp(right)) - Date.parse(getTimestamp(left));
    if (timestampDifference !== 0 || getTieBreaker === undefined) return timestampDifference;
    return getTieBreaker(right).localeCompare(getTieBreaker(left));
  });
  const today = dateKey(now);
  const groups = new Map<string, RecencyQueueGroup<T>>();

  for (const item of sorted) {
    const timestamp = getTimestamp(item);
    const itemDate = dateKey(timestamp);
    const age = ageInDays(timestamp, now);
    const isDayGroup = age < 0 || itemDate === today;
    const weekOffset = Math.floor(Math.max(age, 0) / 7);
    const key = isDayGroup ? itemDate : `week-${weekOffset}`;
    const existing = groups.get(key);
    if (existing !== undefined) {
      existing.items.push(item);
      continue;
    }
    let group: RecencyQueueGroup<T>;
    if (isDayGroup) {
      group = { date: itemDate, items: [item], key: itemDate, kind: "day" };
    } else {
      group = weeklyGroup(weekOffset, today, [item]);
    }
    groups.set(key, group);
  }

  return [...groups.values()];
}

export function reviewQueueWeekLabel(weekOffset: number, language: "fa" | "en"): string {
  if (language === "fa") {
    return weekOffset === 0 ? "این هفته" : `${weekOffset.toLocaleString("fa-IR", { useGrouping: false })} هفته قبل`;
  }
  return weekOffset === 0 ? "This week" : `${weekOffset} ${weekOffset === 1 ? "week" : "weeks"} ago`;
}

export function groupWorkoutReviewQueue(
  items: readonly WorkoutReviewQueueItem[],
  now: string = new Date().toISOString(),
  timestamp: WorkoutReviewQueueTimestamp = "created_at",
): WorkoutReviewQueueGroup[] {
  return groupReviewQueueByRecency(
    items,
    (item) => timestamp === "approved_at" ? item.approved_at ?? item.created_at : item.created_at,
    now,
    (item) => item.id,
  );
}

export type CoachTemplateSelection = {
  selected_template: string;
  explanation_fa: string;
  explanation_en: string;
  score: {
    priority: number;
    body_analysis: number;
    goal: number;
    sex: number;
    fallback: number;
    total: number;
  };
};

export type WorkoutReviewDetail = WorkoutReviewQueueItem & {
  coach_note: string | null;
  draft: { days: WorkoutReviewDayDraft[] } | null;
  source_plan: WorkoutPlan;
  exercise_options: Array<{
    id: string;
    name_en: string;
    name_fa: string;
    prescription_mode?: PrescriptionMode;
    duration_min_seconds?: number | null;
    duration_max_seconds?: number | null;
  }>;
  template_selection: CoachTemplateSelection | null;
  profile_summary?: ReviewProfileSummary | null;
};
