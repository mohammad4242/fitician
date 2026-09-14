import { describe, expect, it } from "vitest";

import {
  groupWorkoutReviewQueue,
  type WorkoutReviewQueueItem,
} from "./workout-reviews.js";

const NOW = "2026-09-14T08:00:00.000Z";

function item(id: string, createdAt: string): WorkoutReviewQueueItem {
  return {
    id,
    source_plan_id: `plan-${id}`,
    user_id: `user-${id}`,
    member_display_name: id,
    member_profile_photo_url: null,
    fitness_goal: "build_muscle",
    experience_level: "beginner",
    status: "pending",
    claimed_by_user_id: null,
    lease_expires_at: null,
    draft_revision: 1,
    created_at: createdAt,
    approved_at: null,
  };
}

function daysAgo(days: number): string {
  const value = new Date(NOW);
  value.setUTCDate(value.getUTCDate() - days);
  return value.toISOString();
}

describe("groupWorkoutReviewQueue", () => {
  it("keeps seven recent calendar days separate and rolls older items into weekly and monthly groups", () => {
    const groups = groupWorkoutReviewQueue(
      [
        item("month", daysAgo(28)),
        item("week-4", daysAgo(21)),
        item("week-3", daysAgo(14)),
        item("week-2", daysAgo(7)),
        ...Array.from({ length: 7 }, (_, index) => item(`day-${index}`, daysAgo(index))),
      ],
      NOW,
    );

    expect(groups.map((group) => group.key)).toEqual([
      "2026-09-14",
      "2026-09-13",
      "2026-09-12",
      "2026-09-11",
      "2026-09-10",
      "2026-09-09",
      "2026-09-08",
      "week-2",
      "week-3",
      "week-4",
      "month",
    ]);
    expect(groups.find((group) => group.key === "week-2")?.items.map(({ id }) => id)).toEqual(["week-2"]);
    expect(groups.find((group) => group.key === "month")?.items.map(({ id }) => id)).toEqual(["month"]);
  });

  it("sorts items newest-first inside a date group", () => {
    const groups = groupWorkoutReviewQueue([
      item("old", "2026-09-14T07:00:00.000Z"),
      item("new", "2026-09-14T07:30:00.000Z"),
    ], NOW);

    expect(groups[0]?.items.map(({ id }) => id)).toEqual(["new", "old"]);
  });

  it("uses Tehran local dates at a midnight boundary", () => {
    const groups = groupWorkoutReviewQueue([
      item("after-midnight", "2026-09-14T20:31:00.000Z"),
      item("before-midnight", "2026-09-14T20:29:00.000Z"),
    ], "2026-09-14T20:30:00.000Z");

    expect(groups.map((group) => group.key)).toEqual(["2026-09-15", "2026-09-14"]);
  });
});
