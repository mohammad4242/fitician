import { request } from "../../shared/apiClient";

import type {
  WorkoutReviewDetail,
  WorkoutReviewMemberDetail,
  WorkoutReviewDraftUpdate,
  WorkoutReviewQueueItem,
  WorkoutReviewQueueView,
} from "./types";

const basePath = "/api/v1/coach/workout-reviews";

export function verifyCoachAccess(): Promise<{ authorized: true }> {
  return request(`${basePath}/access`);
}

export function listWorkoutReviews(
  view: WorkoutReviewQueueView,
): Promise<WorkoutReviewQueueItem[]> {
  return request(`${basePath}?view=${view}`);
}

export function getWorkoutReview(reviewId: string): Promise<WorkoutReviewDetail> {
  return request(`${basePath}/${reviewId}`);
}

export function claimWorkoutReview(reviewId: string): Promise<WorkoutReviewDetail> {
  return request(`${basePath}/${reviewId}/claim`, { method: "POST" });
}

export function renewWorkoutReview(reviewId: string): Promise<WorkoutReviewDetail> {
  return request(`${basePath}/${reviewId}/renew`, { method: "POST" });
}

export function saveWorkoutReviewDraft(
  reviewId: string,
  payload: WorkoutReviewDraftUpdate,
): Promise<WorkoutReviewDetail> {
  return request(`${basePath}/${reviewId}/draft`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function approveWorkoutReview(
  reviewId: string,
  expectedRevision: number,
): Promise<WorkoutReviewDetail> {
  return request(`${basePath}/${reviewId}/submit`, {
    method: "POST",
    body: JSON.stringify({ expected_revision: expectedRevision }),
  });
}

export function submitWorkoutReview(
  reviewId: string,
  expectedRevision: number,
): Promise<WorkoutReviewDetail> {
  return approveWorkoutReview(reviewId, expectedRevision);
}

export function rejectWorkoutReview(
  reviewId: string,
  expectedRevision: number,
  explanation: string,
): Promise<WorkoutReviewDetail> {
  return request(`${basePath}/${reviewId}/reject`, {
    method: "POST",
    body: JSON.stringify({ expected_revision: expectedRevision, explanation }),
  });
}

const memberBasePath = "/api/v1/workout-reviews";

export function getCurrentMemberWorkoutReview(): Promise<WorkoutReviewMemberDetail> {
  return request(`${memberBasePath}/current`);
}

export function acceptMemberWorkoutReview(
  reviewId: string,
  expectedRevision: number,
): Promise<WorkoutReviewMemberDetail> {
  return request(`${memberBasePath}/${reviewId}/accept`, {
    method: "POST",
    body: JSON.stringify({ expected_revision: expectedRevision }),
  });
}

export function rejectMemberWorkoutReview(
  reviewId: string,
  expectedRevision: number,
  explanation: string,
): Promise<WorkoutReviewMemberDetail> {
  return request(`${memberBasePath}/${reviewId}/reject`, {
    method: "POST",
    body: JSON.stringify({ expected_revision: expectedRevision, explanation }),
  });
}
