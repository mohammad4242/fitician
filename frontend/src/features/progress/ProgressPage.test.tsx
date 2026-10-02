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
  expect(await screen.findByText("کالری و پایبندی تغذیه")).toBeInTheDocument();
  expect(
    screen.getByText("برای این روز مصرفی ثبت نشده است."),
  ).toBeInTheDocument();
  expect(
    screen.queryByText("پایبندی به جلسه‌های موعدرسیده"),
  ).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "پهنای سرشانه" }));
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
it('keeps one real measurement as a single point without a delta',async()=>{
 mocks.overview.mockResolvedValue({...data,body_measurements:{...data.body_measurements,weight:{unit:'kg',points:[{recorded_at:'2026-10-01T10:00:00Z',value:80,source:'manual'}],start_value:80,latest_value:80,delta:null}}});
 render(<MemoryRouter><ProgressPage /></MemoryRouter>);
 expect(await screen.findByRole('button',{name:/وزن.*۸۰ kg/})).toBeInTheDocument();
 expect(screen.getAllByText('برای نمایش روند، حداقل یک ثبت دیگر لازم است.').length).toBeGreaterThan(0);
});
