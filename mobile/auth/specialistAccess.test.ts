import { expect, it } from "vitest";

import { ApiError, type TransportRequest } from "@fitician/core";

import { loadSpecialistAccess } from "./specialistAccess";

it("grants only the specialist roles confirmed by their backend access endpoints", async () => {
  const requests: TransportRequest[] = [];
  const access = await loadSpecialistAccess(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    if (request.path === "/api/v1/nutrition/physician/access") {
      return { authorized: true } as TResponse;
    }
    return { authorized: false } as TResponse;
  });

  expect(access).toEqual({ coach: "denied", physician: "granted" });
  expect(requests.map((request) => request.path).sort()).toEqual([
    "/api/v1/coach/workout-reviews/access",
    "/api/v1/nutrition/physician/access",
  ]);
});

it("does not expose a role when its access check fails", async () => {
  const access = await loadSpecialistAccess(async () => {
    throw new Error("offline");
  });

  expect(access).toMatchObject({ coach: "error", physician: "error" });
  expect(access.errors?.coach).toBeInstanceOf(Error);
  expect(access.errors?.physician).toBeInstanceOf(Error);
});

it("treats a valid forbidden response as denied but server failures as errors", async () => {
  const access = await loadSpecialistAccess(async (request: TransportRequest) => {
    if (request.path === "/api/v1/coach/workout-reviews/access") {
      throw new ApiError(403, "Forbidden");
    }
    throw new ApiError(503, "Unavailable");
  });

  expect(access).toMatchObject({ coach: "denied", physician: "error" });
  expect(access.errors?.physician).toBeInstanceOf(ApiError);
});

it("treats malformed access responses as errors", async () => {
  const access = await loadSpecialistAccess(async <TResponse>() => ({ authorized: "yes" } as TResponse));

  expect(access).toMatchObject({ coach: "error", physician: "error" });
  expect(access.errors?.coach).toBeInstanceOf(Error);
  expect(access.errors?.physician).toBeInstanceOf(Error);
});

it("returns granted access after a retry succeeds", async () => {
  let attempt = 0;
  const request = async <TResponse>(_input: TransportRequest) => {
    attempt += 1;
    if (attempt <= 2) throw new Error("temporary outage");
    return { authorized: true } as TResponse;
  };

  await expect(loadSpecialistAccess(request)).resolves.toMatchObject({ coach: "error", physician: "error" });
  await expect(loadSpecialistAccess(request)).resolves.toMatchObject({ coach: "granted", physician: "granted" });
});
