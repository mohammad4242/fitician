import { expect, it } from "vitest";

import type { TransportRequest } from "@fitician/core";

import { createWorkoutReviewApi } from "./workoutReviewApi";

it("uses the member workout review contract for current, accept, and reject", async () => {
  const requests: TransportRequest[] = [];
  const api = createWorkoutReviewApi(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    return {} as TResponse;
  });

  await api.getCurrent();
  await api.accept("review-1", 3);
  await api.reject("review-1", 3, "حرکت روز اول نیاز به اصلاح دارد");

  expect(requests).toEqual([
    { method: "GET", path: "/api/v1/workout-reviews/current" },
    {
      body: { expected_revision: 3 },
      method: "POST",
      path: "/api/v1/workout-reviews/review-1/accept",
    },
    {
      body: { expected_revision: 3, explanation: "حرکت روز اول نیاز به اصلاح دارد" },
      method: "POST",
      path: "/api/v1/workout-reviews/review-1/reject",
    },
  ]);
});
