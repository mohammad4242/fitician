import { describe, expect, it } from "vitest";

import {
  groupReviewQueueByRecency,
  groupWorkoutReviewQueue,
  reviewQueueWeekLabel,
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
  it("keeps today separate and rolls older items into explicit weekly groups", () => {
    const groups = groupWorkoutReviewQueue(
      [
        item("week-4", daysAgo(28)),
        item("week-3", daysAgo(21)),
        item("week-2", daysAgo(14)),
        item("week-1", daysAgo(7)),
        ...Array.from({ length: 7 }, (_, index) => item(`day-${index}`, daysAgo(index))),
      ],
      NOW,
    );

    expect(groups.map((group) => group.key)).toEqual([
      "2026-09-14",
      "week-0",
      "week-1",
      "week-2",
      "week-3",
      "week-4",
    ]);
    expect(groups.find((group) => group.key === "week-1")?.items.map(({ id }) => id)).toEqual(["week-1"]);
    expect(groups.find((group) => group.key === "week-4")?.items.map(({ id }) => id)).toEqual(["week-4"]);
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

    expect(groups.map((group) => group.key)).toEqual(["2026-09-15", "week-0"]);
  });

  it("groups approved reviews by approval date when requested", () => {
    const approved = {
      ...item("approved", daysAgo(28)),
      status: "approved" as const,
      approved_at: daysAgo(1),
    };

    const groups = groupWorkoutReviewQueue([approved], NOW, "approved_at");

    expect(groups[0]?.key).toBe("week-0");
    expect(groups[0]?.items[0]).toBe(approved);
  });
});

describe("groupReviewQueueByRecency", () => {
  it("groups any queue item using its selected sent timestamp", () => {
    const cases = [
      { review_id: "older", requested_at: "2026-08-10T08:00:00.000Z" },
      { review_id: "today", requested_at: "2026-09-14T07:00:00.000Z" },
    ];

    const groups = groupReviewQueueByRecency(cases, (review) => review.requested_at, NOW);

    expect(groups.map((group) => group.key)).toEqual(["2026-09-14", "week-5"]);
    expect(groups[0]?.items).toEqual([cases[1]]);
    expect(groups[1]?.items).toEqual([cases[0]]);
  });

  it("keeps today separate and exposes real week offsets beyond four", () => {
    const cases = [
      { review_id: "today", requested_at: daysAgo(0) },
      { review_id: "current-week", requested_at: daysAgo(1) },
      { review_id: "one-week", requested_at: daysAgo(7) },
      { review_id: "two-weeks", requested_at: daysAgo(14) },
      { review_id: "four-weeks", requested_at: daysAgo(28) },
      { review_id: "five-weeks", requested_at: daysAgo(35) },
    ];

    const groups = groupReviewQueueByRecency(cases, (review) => review.requested_at, NOW);

    expect(groups.map((group) => group.key)).toEqual([
      "2026-09-14",
      "week-0",
      "week-1",
      "week-2",
      "week-4",
      "week-5",
    ]);
    expect(groups[1]).toMatchObject({
      endDate: "2026-09-13",
      kind: "week",
      startDate: "2026-09-08",
      weekOffset: 0,
    });
    expect(groups[2]).toMatchObject({
      endDate: "2026-09-07",
      kind: "week",
      startDate: "2026-09-01",
      weekOffset: 1,
    });
    expect(groups[4]).toMatchObject({
      endDate: "2026-08-17",
      kind: "week",
      startDate: "2026-08-11",
      weekOffset: 4,
    });
  });

  it("formats week labels from the explicit offset", () => {
    expect(reviewQueueWeekLabel(0, "fa")).toBe("این هفته");
    expect(reviewQueueWeekLabel(1, "fa")).toBe("۱ هفته قبل");
    expect(reviewQueueWeekLabel(4, "fa")).toBe("۴ هفته قبل");
    expect(reviewQueueWeekLabel(4, "fa")).not.toContain("هفتهٔ 4");
  });
});
