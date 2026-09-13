import { expect, it } from "vitest";

import type { TransportRequest } from "@fitician/core";

import { createProgramTimelineApi } from "./programTimelineApi";

it("requests today's program timeline with the device timezone", async () => {
  const requests: TransportRequest[] = [];
  const timeline = { local_date: "2026-09-13", timezone: "Asia/Tehran" };
  const api = createProgramTimelineApi(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    return timeline as TResponse;
  });

  await expect(api.getToday("Asia/Tehran")).resolves.toBe(timeline);
  expect(requests).toEqual([
    {
      method: "GET",
      path: "/api/v1/program-timeline/today?timezone=Asia%2FTehran",
    },
  ]);
});

it("encodes timezone names without changing the request path", async () => {
  const requests: TransportRequest[] = [];
  const api = createProgramTimelineApi(async <TResponse>(request: TransportRequest) => {
    requests.push(request);
    return {} as TResponse;
  });

  await api.getToday("America/Argentina/Buenos_Aires");

  expect(requests[0]).toEqual({
    method: "GET",
    path: "/api/v1/program-timeline/today?timezone=America%2FArgentina%2FBuenos_Aires",
  });
});
