import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, expect, it, vi } from "vitest";

import "../i18n";

const logout = vi.fn(async () => undefined);
const auth = vi.hoisted(() => ({ isAdmin: false }));
const profileState = vi.hoisted(() => ({ productMode: "both" as "both" | "training" | "nutrition" }));
const entitlementState = vi.hoisted(() => ({ snapshot: null as unknown }));

vi.mock("../features/auth/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", email: "member@example.com", created_at: "2026-08-11", is_admin: auth.isAdmin },
    logout,
  }),
}));

vi.mock("../features/profile/ProfileContext", () => ({
  useProfile: () => ({
    profile: { display_name: "محمد" },
    productMode: profileState.productMode,
    status: "ready",
  }),
}));
vi.mock("../features/entitlements/EntitlementContext", () => ({
  useEntitlements: () => ({
    snapshot: entitlementState.snapshot,
    loading: false,
    error: null,
    refresh: vi.fn(async () => undefined),
    retry: vi.fn(),
    hasEntitlement: () => true,
    quotaFor: () => null,
  }),
}));

vi.mock("../features/nutrition/api", () => ({ verifyPhysicianAccess: vi.fn(async () => { throw new Error("denied"); }) }));
vi.mock("../features/workoutReviews/api", () => ({ verifyCoachAccess: vi.fn(async () => { throw new Error("denied"); }) }));

import { MorePage } from "./MorePage";

beforeEach(() => {
  entitlementState.snapshot = null;
});

it("signs out from the separated account action", async () => {
  auth.isAdmin = false;
  const user = userEvent.setup();
  render(<MemoryRouter><MorePage /></MemoryRouter>);

  await user.click(screen.getByRole("button", { name: "خروج از حساب" }));

  expect(logout).toHaveBeenCalledOnce();
});

it("shows the training program library in the mobile admin workspace", () => {
  auth.isAdmin = true;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.getByRole("link", { name: /کتابخانه برنامه‌های تمرینی/ })).toHaveAttribute(
    "href",
    "/admin/training-program-templates",
  );
});

it("shows the current launch trial in the access summary", () => {
  entitlementState.snapshot = {
    primary_package: "launch_trial",
    trial: { active: true, ends_at: "2026-09-30T12:00:00Z" },
  };

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.getByText("دوره آزمایشی شروع")).toBeInTheDocument();
  expect(screen.getByText(/آزمایشی تا/)).toBeInTheDocument();
});

it("links access management and shows a paid access end date", () => {
  entitlementState.snapshot = {
    primary_package: "training",
    active_packages: ["training"],
    trial: { active: false, ends_at: null },
    entitlements: { granted: ["training.plan.generate"], quotas: [] },
    grants: [{
      id: "grant-1",
      package_code: "training",
      source: "subscription",
      term_weeks: 4,
      starts_at: "2026-09-13T12:00:00Z",
      ends_at: "2026-10-11T12:00:00Z",
      revoked_at: null,
    }],
  };

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.getByRole("link", { name: "مشاهده پلن‌ها" })).toHaveAttribute("href", "/plans");
  expect(screen.getByRole("link", { name: "تاریخچه خرید" })).toHaveAttribute("href", "/billing/history");
  expect(screen.getByText(/پایان دسترسی/)).toBeInTheDocument();
});

it("shows the nutrition program catalogue in the mobile admin workspace", () => {
  auth.isAdmin = true;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.getByRole("link", { name: /کاتالوگ برنامه‌های غذایی/ })).toHaveAttribute(
    "href",
    "/admin/nutrition-programs",
  );
});

it("shows AI settings in the mobile admin workspace", () => {
  auth.isAdmin = true;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.getByRole("link", { name: /تنظیمات هوش مصنوعی/ })).toHaveAttribute(
    "href",
    "/admin/ai-settings",
  );
});

it("shows billing offer management in the admin workspace", () => {
  auth.isAdmin = true;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.getByRole("link", { name: /پیشنهادهای پرداخت/ })).toHaveAttribute("href", "/admin/billing");
});

it("hides AI settings from non-admin members", () => {
  auth.isAdmin = false;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.queryByRole("link", { name: /تنظیمات هوش مصنوعی/ })).not.toBeInTheDocument();
});

it("does not show a separate exercise administration workspace", () => {
  auth.isAdmin = true;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  expect(screen.queryByRole("link", { name: /مدیریت حرکات/ })).not.toBeInTheDocument();
  expect(screen.getByRole("link", { name: /کتابخانه حرکات/ })).toHaveAttribute("href", "/exercises");
});

it("shows the meal catalogue in the product group for non-admin members", () => {
  auth.isAdmin = false;
  profileState.productMode = "both";

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  const productGroup = screen.getByRole("region", { name: "محصول" });
  expect(within(productGroup).getByRole("link", { name: /کاتالوگ وعده‌های غذایی/ })).toHaveAttribute(
    "href",
    "/meal-catalogue",
  );
  expect(screen.queryByRole("link", { name: /فضاهای تخصصی/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "/admin/nutrition-meals" })).not.toBeInTheDocument();
});

it("shows the meal catalogue for training-only members", () => {
  auth.isAdmin = false;
  profileState.productMode = "training";

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  const productGroup = screen.getByRole("region", { name: "محصول" });
  expect(within(productGroup).getByRole("link", { name: /کاتالوگ وعده‌های غذایی/ })).toHaveAttribute(
    "href",
    "/meal-catalogue",
  );
  expect(within(productGroup).queryByRole("link", { name: /کاتالوگ مواد غذایی/ })).not.toBeInTheDocument();
});

it("shows public privacy and deletion controls in the account group", () => {
  auth.isAdmin = false;

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  const accountGroup = screen.getByRole("region", { name: "حساب" });
  expect(within(accountGroup).getByRole("link", { name: /حذف حساب/ })).toHaveAttribute(
    "href",
    "/delete-account",
  );
  expect(within(accountGroup).getByRole("link", { name: /سیاست حریم خصوصی/ })).toHaveAttribute(
    "href",
    "/privacy",
  );
});

it("shows single meal catalogue in product and no duplicate in workspaces for administrators", () => {
  auth.isAdmin = true;
  profileState.productMode = "both";

  render(<MemoryRouter><MorePage /></MemoryRouter>);

  const productGroup = screen.getByRole("region", { name: "محصول" });
  expect(within(productGroup).getByRole("link", { name: /کاتالوگ وعده‌های غذایی/ })).toHaveAttribute(
    "href",
    "/meal-catalogue",
  );

  const workspacesGroup = screen.getByRole("region", { name: "فضاهای تخصصی" });
  expect(within(workspacesGroup).queryByRole("link", { name: /کاتالوگ وعده‌های غذایی/ })).not.toBeInTheDocument();
  expect(screen.queryByRole("link", { name: "/admin/nutrition-meals" })).not.toBeInTheDocument();
});
