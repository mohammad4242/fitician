import { expect, it } from "vitest";

import type { NotificationResponse } from "expo-notifications";

import {
  isNotificationRoutePath,
  notificationPathFromData,
  notificationPathFromResponse,
} from "./notificationRouting";

it("maps domain notification events to authenticated native destinations", () => {
  expect(notificationPathFromData({ event_type: "workout_plan_approved" })).toBe(
    "/member/workouts",
  );
  expect(notificationPathFromData({ event_type: "workout_plan_acceptance_required" })).toBe(
    "/member/workouts",
  );
  expect(notificationPathFromData({ event_type: "workout_plan_changes_requested" })).toBe("/coach");
  expect(notificationPathFromData({ event_type: "nutrition_plan_approved" })).toBe(
    "/member/nutrition",
  );
  expect(notificationPathFromData({ event_type: "food_photo_analysis_completed" })).toBe(
    "/member/nutrition",
  );
  expect(notificationPathFromData({ event_type: "food_photo_analysis_failed" })).toBe(
    "/member/nutrition",
  );
  expect(notificationPathFromData({ event_type: "body_analysis_completed" })).toBe(
    "/member/body-analysis-history",
  );
  expect(notificationPathFromData({ event_type: "weekly_check_in_due" })).toBe(
    "/member/workouts",
  );
  expect(notificationPathFromData({ event_type: "workout_review_required" })).toBe("/coach");
  expect(notificationPathFromData({ event_type: "nutrition_review_required" })).toBe(
    "/physician",
  );
  expect(
    notificationPathFromData({
      event_type: "body_analysis_review_required",
      recipient_role: "coach",
    }),
  ).toBe("/coach");
  expect(
    notificationPathFromData({
      event_type: "body_analysis_review_required",
      recipient_role: "doctor",
    }),
  ).toBe("/physician");
});

it("extracts notification data without trusting arbitrary routes or resource ids", () => {
  const response = {
    notification: {
      request: {
        content: {
          data: {
            event_type: "physician_plan_rejected",
            plan_id: "not-used-as-a-route",
            path: "/admin",
          },
        },
      },
    },
  } as unknown as NotificationResponse;

  expect(notificationPathFromResponse(response)).toBe("/member/nutrition");
  expect(notificationPathFromData({ event_type: "unknown_event", path: "/admin" })).toBeNull();
  expect(notificationPathFromData({ event_type: "body_analysis_review_required" })).toBeNull();
  expect(isNotificationRoutePath("/admin")).toBe(false);
  expect(isNotificationRoutePath("/member/workouts")).toBe(true);
  expect(notificationPathFromResponse(null)).toBeNull();
});

it("routes personal reminders and program messages to authenticated app screens", () => {
  expect(notificationPathFromData({ event_type: "training_reminder" })).toBe("/member/workouts");
  expect(notificationPathFromData({ event_type: "nutrition_reminder" })).toBe("/member/nutrition");
  expect(notificationPathFromData({ event_type: "program_message" })).toBe("/notifications");
  expect(notificationPathFromData({ event_type: "return_reminder" })).toBe("/member");
});
it('opens a support ticket directly and rejects unsafe IDs',()=>{
 const id='12345678-1234-4234-8234-123456789abc';
 expect(notificationPathFromData({event_type:'support_ticket_reply',ticket_id:id})).toBe(`/member/support-ticket/${id}`);
 expect(isNotificationRoutePath(`/member/support-ticket/${id}`)).toBe(true);
 expect(isNotificationRoutePath('/member/support-ticket/../admin')).toBe(false);
 expect(notificationPathFromData({event_type:'support_ticket_reply',ticket_id:'../admin'})).toBeNull();
});
