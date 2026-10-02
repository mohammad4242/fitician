import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";
import { ProgressPage } from "./ProgressPage";
const mocks = vi.hoisted(() => ({
  overview: vi.fn(),
  recordMeasurement: vi.fn(),
}));
vi.mock("./api", () => ({ progressApi: mocks }));
vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: { id: "member" } }),
}));
vi.mock("../entitlements/EntitlementContext", () => ({
  useEntitlements: () => ({
    loading: false,
    hasEntitlement: () => true,
    quotaFor: () => null,
  }),
}));
const body = {
  unit: "cm",
  points: [],
  start_value: null,
  latest_value: null,
  delta: null,
};
const data = {
  context: {
    preset: "week",
    timezone: "UTC",
    today: "2026-10-02",
    start_date: "2026-09-26",
    end_date: "2026-10-02",
    training_enabled: false,
    nutrition_enabled: true,
  },
  training: null,
  nutrition: {
    series: [
      {
        date: "2026-10-01",
        target_kcal: 2200,
        actual_kcal: null,
        logging_state: "missing",
        in_progress: false,
      },
    ],
    logged_days: 0,
    elapsed_days: 6,
    adherent_days: 0,
    comparable_days: 0,
    average_difference_kcal: null,
  },
  body_measurements: {
    weight: { ...body, unit: "kg" },
    waist: body,
    hip: body,
    shoulder_width: body,
  },
  body_analysis: {},
  recovery: [],
  insights: [],
};
it("renders nutrition-only mode with missing intake and metric selector", async () => {
  mocks.overview.mockResolvedValue(data);
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  expect(await screen.findByText("کالری و پایبندی")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /کالری و پایبندی/ }));
  expect(
    await screen.findByText("برای این روز مصرفی ثبت نشده است."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("پایبندی به جلسه‌های موعدرسیده"),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "بدن" }));
  fireEvent.click(await screen.findByRole("button", { name: "پهنای سرشانه" }));
  expect(screen.getByRole("button", { name: "پهنای سرشانه" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  expect(screen.queryByText("0 kcal")).not.toBeInTheDocument();
});
it("renders a retryable error without invented metrics", async () => {
  mocks.overview.mockRejectedValue(new Error("offline"));
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "دریافت پیشرفت ناموفق بود",
  );
  expect(screen.queryByText("۷۵٪")).not.toBeInTheDocument();
});
it("keeps one real measurement as a single point without a delta", async () => {
  mocks.overview.mockResolvedValue({
    ...data,
    body_measurements: {
      ...data.body_measurements,
      weight: {
        unit: "kg",
        points: [
          { recorded_at: "2026-10-01T10:00:00Z", value: 80, source: "manual" },
        ],
        start_value: 80,
        latest_value: 80,
        delta: null,
      },
    },
  });
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  expect(
    await screen.findByRole("button", { name: /وزن و اندازه‌های بدن.*۸۰ kg/ }),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText("برای نمایش روند، حداقل یک ثبت دیگر لازم است.").length,
  ).toBeGreaterThan(0);
});

it("opens Overview and drills into Calories without refetching", async () => {
  mocks.overview.mockResolvedValue(data);
  mocks.overview.mockClear();
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  expect(await screen.findByRole("tab", { name: "نمای کلی" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    screen.queryByRole("group", { name: /کالری هدف/ }),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /کالری و پایبندی/ }));
  expect(screen.getByRole("tab", { name: "کالری" })).toHaveAttribute(
    "aria-selected",
    "true",
  );
  expect(
    await screen.findByText("برای این روز مصرفی ثبت نشده است."),
  ).toBeInTheDocument();
  expect(mocks.overview).toHaveBeenCalledTimes(1);
});

const training = {
  planned_sessions: 4,
  due_sessions: 4,
  completed_sessions: 3,
  adherence_percent: 75,
  skipped_sessions: 1,
  rescheduled_sessions: 2,
  overdue_sessions: 0,
  weeks: [{ start_date: "2026-09-26", planned: 4, completed: 3 }],
};
vi.mock("../bodyPhotos/BodyProgressPage", () => ({
  BodyProgressPage: () => <div>analysis-history-mounted</div>,
}));
it("loads Body Analysis only on selection", async () => {
  mocks.overview.mockResolvedValue(data);
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  await screen.findByText("کالری و پایبندی");
  expect(
    screen.queryByText("analysis-history-mounted"),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("tab", { name: "تحلیل بدن" }));
  expect(
    await screen.findByText("analysis-history-mounted"),
  ).toBeInTheDocument();
});
it("uses RTL arrow navigation and skips disabled categories", async () => {
  mocks.overview.mockResolvedValue(data);
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  await screen.findByText("کالری و پایبندی");
  fireEvent.keyDown(screen.getByRole("tab", { name: "نمای کلی" }), {
    key: "ArrowLeft",
  });
  expect(screen.getByRole("tab", { name: "کالری" })).toHaveFocus();
  fireEvent.keyDown(screen.getByRole("tab", { name: "بدن" }), {
    key: "ArrowLeft",
  });
  expect(screen.getByRole("tab", { name: "تحلیل بدن" })).toHaveFocus();
});
it("renders true training counts with nutrition disabled", async () => {
  mocks.overview.mockResolvedValue({
    ...data,
    context: {
      ...data.context,
      training_enabled: true,
      nutrition_enabled: false,
    },
    training,
    nutrition: null,
  });
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  fireEvent.click(await screen.findByRole("button", { name: /تمرین.*۳ از ۴/ }));
  expect(await screen.findByText("۷۵%")).toBeInTheDocument();
  expect(screen.getByRole("img")).toHaveAccessibleName(/۴.*۳/);
  expect(screen.getByText("جابه‌جا شده")).toHaveTextContent("۲");
  expect(screen.queryByText("کالری و پایبندی")).not.toBeInTheDocument();
});
it.each([0, 1, 2])(
  "shows recovery with %s check-ins without inventing a trend",
  async (count) => {
    mocks.overview.mockResolvedValue({
      ...data,
      context: { ...data.context, training_enabled: true },
      training,
      recovery: Array.from({ length: count }, (_, i) => ({
        recorded_at: `2026-10-0${i + 1}T10:00:00Z`,
        recovery: "good",
        difficulty: "appropriate",
        week_number: i + 1,
      })),
    });
    render(
      <MemoryRouter>
        <ProgressPage />
      </MemoryRouter>,
    );
    await screen.findByText("کالری و پایبندی");
    fireEvent.click(screen.getByRole("tab", { name: "ریکاوری" }));
    await screen.findByRole("heading", { name: "ریکاوری" });
    expect(
      screen.queryAllByRole("group", { name: /وزن|ریکاوری/ }),
    ).toHaveLength(count > 1 ? 1 : 0);
    if (!count)
      expect(
        screen.getByText(
          "بعد از اولین چک‌این، ریکاوری اینجا نمایش داده می‌شود.",
        ),
      ).toBeInTheDocument();
  },
);
it.each([0, 1, 2])(
  "shows body with %s records and a truthful change",
  async (count) => {
    mocks.overview.mockResolvedValue({
      ...data,
      body_measurements: {
        ...data.body_measurements,
        weight: {
          ...body,
          unit: "kg",
          points: Array.from({ length: count }, (_, i) => ({
            recorded_at: `2026-10-0${i + 1}T10:00:00Z`,
            value: 80 - i,
            source: "manual",
          })),
          start_value: count ? 80 : null,
          latest_value: count ? 81 - count : null,
          delta: count > 1 ? -1 : null,
        },
      },
    });
    render(
      <MemoryRouter>
        <ProgressPage />
      </MemoryRouter>,
    );
    await screen.findByText("کالری و پایبندی");
    fireEvent.click(screen.getByRole("tab", { name: "بدن" }));
    await screen.findByRole("heading", { name: "وزن" });
    expect(
      screen.queryAllByRole("group", { name: /وزن|ریکاوری/ }),
    ).toHaveLength(count > 1 ? 1 : 0);
    expect(screen.queryByText(/→/)).not.toBeInTheDocument();
    if (count === 1)
      expect(
        screen.getByText("برای نمایش روند، حداقل یک ثبت دیگر لازم است."),
      ).toBeInTheDocument();
    if (count > 1) expect(screen.getByText(/−۱ kg/)).toBeInTheDocument();
  },
);
it("selects historical calories and missing intake by chart date", async () => {
  mocks.overview.mockResolvedValue({
    ...data,
    nutrition: {
      ...data.nutrition,
      series: [
        { date: "2026-10-01", target_kcal: 2200, actual_kcal: 2140 },
        {
          date: "2026-10-02",
          target_kcal: 2000,
          actual_kcal: null,
          logging_state: "missing",
        },
      ],
    },
  });
  render(
    <MemoryRouter>
      <ProgressPage />
    </MemoryRouter>,
  );
  fireEvent.click(
    await screen.findByRole("button", { name: /کالری و پایبندی/ }),
  );
  const first = await screen.findByRole("button", {
    name: /کالری هدف ۲٬۲۰۰.*۲٬۱۴۰/,
  });
  fireEvent.focus(first);
  expect(screen.getByText(/−۶۰ kcal/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: /کالری هدف ۲٬۰۰۰.*—/ }));
  expect(
    screen.getByText("برای این روز مصرفی ثبت نشده است."),
  ).toBeInTheDocument();
  expect(screen.queryByText(/−۶۰ kcal/)).not.toBeInTheDocument();
});
