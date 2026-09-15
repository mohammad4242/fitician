import { ApiError, type components, type TransportRequest } from "@fitician/core";

export type MemberWorkoutReview = components["schemas"]["WorkoutReviewMemberDetailResponse"];

export type AuthenticatedWorkoutReviewRequest = <TResponse>(
  request: TransportRequest,
) => Promise<TResponse>;

export interface WorkoutReviewApi {
  accept(reviewId: string, expectedRevision: number): Promise<MemberWorkoutReview>;
  getCurrent(): Promise<MemberWorkoutReview | null>;
  reject(reviewId: string, expectedRevision: number, explanation: string): Promise<MemberWorkoutReview>;
}

const reviewPath = "/api/v1/workout-reviews";

function jsonBody(value: object): TransportRequest["body"] {
  return value as TransportRequest["body"];
}

function detailPath(reviewId: string): string {
  return `${reviewPath}/${encodeURIComponent(reviewId)}`;
}

export function createWorkoutReviewApi(
  request: AuthenticatedWorkoutReviewRequest,
): WorkoutReviewApi {
  return {
    accept: (reviewId, expectedRevision) => request<MemberWorkoutReview>({
      body: jsonBody({ expected_revision: expectedRevision }),
      method: "POST",
      path: `${detailPath(reviewId)}/accept`,
    }),
    async getCurrent() {
      try {
        return await request<MemberWorkoutReview>({
          method: "GET",
          path: `${reviewPath}/current`,
        });
      } catch (error) {
        if (error instanceof ApiError && error.status === 404) return null;
        throw error;
      }
    },
    reject: (reviewId, expectedRevision, explanation) => request<MemberWorkoutReview>({
      body: jsonBody({ expected_revision: expectedRevision, explanation }),
      method: "POST",
      path: `${detailPath(reviewId)}/reject`,
    }),
  };
}
