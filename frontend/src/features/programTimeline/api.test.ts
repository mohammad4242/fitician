import { afterEach, expect, it, vi } from "vitest";

import { getProgramTimelineToday } from "./api";

afterEach(() => vi.restoreAllMocks());

it("requests today's timeline with the current browser timezone", async () => {
  const timeline = { local_date: "2026-09-14", timezone: "Asia/Tehran" };
  vi.spyOn(globalThis, "fetch").mockResolvedValue(Response.json(timeline));

  await expect(getProgramTimelineToday("Asia/Tehran")).resolves.toEqual(timeline);
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/program-timeline/today?timezone=Asia%2FTehran",
    expect.objectContaining({ credentials: "include" }),
  );
});

