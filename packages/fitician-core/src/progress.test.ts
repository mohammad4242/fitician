import { expect, it, vi } from "vitest";
import { createProgressApi, chartGeometry } from "./progress.js";
import type { TransportRequest } from "./transport.js";
it("keeps missing chart values as gaps and uses actual observation timestamps", () => {
  const chart = chartGeometry(
    [
      [
        { date: "2026-10-01", value: 100 },
        { date: "2026-10-02", value: null },
        { date: "2026-10-03", value: 110 },
      ],
    ],
    320,
    200,
  );
  expect(chart.lines[0].segments).toHaveLength(2);
  expect(chart.lines[0].points).toHaveLength(2);
  expect(chart.lines[0].points[0].index).toBe(0);
  expect(chart.lines[0].points[1].index).toBe(2);
  expect(chartGeometry([[]], 320, 200).lines[0].points).toEqual([]);
});
it("shares one authoritative overview and canonical measurement endpoint", async () => {
  const request = vi.fn(async (_input: TransportRequest) => ({
    context: { today: "2026-10-02" },
  }));
  const api = createProgressApi(request as never);
  await api.overview("four_weeks", "Asia/Tehran");
  expect(request.mock.calls[0][0].path).toBe(
    "/api/v1/progress/overview?preset=four_weeks&timezone=Asia%2FTehran",
  );
  await api.recordMeasurement({ request_id: "id", shoulder_width_cm: 45 });
  expect(request.mock.calls[1][0]).toMatchObject({
    path: "/api/v1/profile/body-measurements",
    body: { shoulder_width_cm: 45 },
  });
});
it("keeps categorical recovery on its explicit reported-state scale", () => {
  const chart = chartGeometry(
    [
      [
        { date: "2026-10-01", value: 3 },
        { date: "2026-10-02", value: 3 },
      ],
    ],
    320,
    200,
    [1, 3],
  );
  expect(chart.minY).toBe(1);
  expect(chart.maxY).toBe(3);
  expect(chart.lines[0].points).toHaveLength(2);
  expect(
    chart.lines[0].points.every((point) => point.y === chart.padding.top),
  ).toBe(true);
});
