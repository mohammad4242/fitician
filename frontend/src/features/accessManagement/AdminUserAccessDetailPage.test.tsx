import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import "../../i18n";

const accessApi = vi.hoisted(() => ({
  adminAccessPackageCodes: ["training", "training_coach", "complete", "complete_care"],
  getCampaigns: vi.fn(),
  getUserAccess: vi.fn(),
  grantUserAccess: vi.fn(),
  redeemUserCampaign: vi.fn(),
  revokeUserAccess: vi.fn(),
}));
vi.mock("./adminAccessApi", () => accessApi);

import { AdminUserAccessDetailPage } from "./AdminUserAccessDetailPage";

const access = {
  member: {
    user_id: "member-1",
    display_name: "علی رضایی",
    email: "ali@example.com",
    phone_number: null,
    created_at: "2026-09-13T08:00:00Z",
    primary_package: "complete" as const,
    active_packages: ["complete"] as const,
    trial_active: false,
    trial_ends_at: null,
    paid_access_end: "2026-11-13T08:00:00Z",
  },
  entitlement_snapshot: {
    primary_package: "complete" as const,
    active_packages: ["complete"] as const,
    granted_entitlements: ["training.plan.generate", "body_analysis.run"] as const,
    trial_active: false,
    trial_ends_at: null,
  },
  grants: [
    {
      id: "subscription-grant",
      package_code: "complete" as const,
      source: "subscription" as const,
      term_weeks: 8 as const,
      starts_at: "2026-09-13T08:00:00Z",
      ends_at: "2026-11-13T08:00:00Z",
      revoked_at: null,
      created_at: "2026-09-13T08:00:00Z",
      status: "active" as const,
      is_currently_active: true,
      billing_order_id: "order-1",
      campaign_id: null,
      campaign_name: null,
    },
    {
      id: "revoked-grant",
      package_code: "training_coach" as const,
      source: "admin" as const,
      term_weeks: 4 as const,
      starts_at: "2026-08-01T08:00:00Z",
      ends_at: "2026-09-01T08:00:00Z",
      revoked_at: "2026-08-20T08:00:00Z",
      created_at: "2026-08-01T08:00:00Z",
      status: "revoked" as const,
      is_currently_active: false,
      billing_order_id: null,
      campaign_id: null,
      campaign_name: null,
    },
  ],
};

const campaign = {
  id: "campaign-1",
  code: "beta-promotion",
  name: "Beta promotion",
  description: null,
  kind: "manual_promotion" as const,
  package_code: "training_coach" as const,
  duration_days: 30,
  term_weeks: 4 as const,
  available_from: null,
  available_until: null,
  is_active: true,
  max_total_redemptions: null,
  redemption_count: 0,
  created_by_user_id: null,
  created_at: "2026-09-13T08:00:00Z",
  updated_at: "2026-09-13T08:00:00Z",
};

beforeEach(() => {
  accessApi.getUserAccess.mockReset();
  accessApi.getCampaigns.mockReset();
  accessApi.grantUserAccess.mockReset();
  accessApi.redeemUserCampaign.mockReset();
  accessApi.revokeUserAccess.mockReset();
  accessApi.getUserAccess.mockResolvedValue(access);
  accessApi.getCampaigns.mockResolvedValue([campaign]);
  accessApi.grantUserAccess.mockResolvedValue(access.grants[0]);
  accessApi.redeemUserCampaign.mockResolvedValue({ campaign, grant: access.grants[1] });
  accessApi.revokeUserAccess.mockResolvedValue({ ...access.grants[0], status: "revoked" });
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={["/admin/billing/users/member-1"]}>
      <Routes>
        <Route path="/admin/billing/users/:userId" element={<AdminUserAccessDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

it("shows identity, entitlement snapshot, and clearly labeled grant history", async () => {
  renderDetail();

  expect(await screen.findByRole("heading", { name: "علی رضایی" })).toBeInTheDocument();
  expect(screen.getByText("خلاصه دسترسی‌ها")).toBeInTheDocument();
  expect(screen.getByText("ACTIVE")).toBeInTheDocument();
  expect(screen.getByText("REVOKED")).toBeInTheDocument();
  expect(screen.getByText("اشتراک")).toBeInTheDocument();
  expect(screen.queryByRole("checkbox", { name: /training\.plan|body_analysis/ })).not.toBeInTheDocument();
});

it("grants a package and applies a manual campaign with a reason", async () => {
  const user = userEvent.setup();
  renderDetail();

  await user.click(await screen.findByRole("button", { name: "اعطای دسترسی" }));
  expect(screen.queryByRole("option", { name: "دوره آزمایشی شروع" })).not.toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText("بسته"), "training_coach");
  await user.selectOptions(screen.getByLabelText("مدت تمرین"), "4");
  await user.click(screen.getByRole("button", { name: "پایان" }));
  await user.click(screen.getByRole("button", { name: "انتخاب" }));
  await user.type(screen.getByLabelText("دلیل"), "beta tester");
  expect(screen.queryByLabelText("کلید درخواست")).not.toBeInTheDocument();
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.grantUserAccess).toHaveBeenCalledWith("member-1", expect.objectContaining({
    package_code: "training_coach",
    term_weeks: 4,
    ends_at: expect.any(String),
    reason: "beta tester",
    client_idempotency_key: expect.any(String),
  }));

  await user.click(screen.getByRole("button", { name: "اعمال کمپین" }));
  await user.selectOptions(screen.getByLabelText("کمپین را انتخاب کنید"), "campaign-1");
  await user.type(screen.getByLabelText("دلیل اعمال کمپین"), "manual beta access");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  expect(accessApi.redeemUserCampaign).toHaveBeenCalledWith(
    "member-1",
    "campaign-1",
    "manual beta access",
  );
});

it("generates one hidden grant idempotency key and reuses it for retries", async () => {
  const user = userEvent.setup();
  const randomUUID = vi.fn().mockReturnValue("generated-grant-key");
  vi.stubGlobal("crypto", { randomUUID });
  accessApi.grantUserAccess
    .mockRejectedValueOnce(new Error("retry"))
    .mockResolvedValueOnce(access.grants[0]);
  renderDetail();

  await user.click(await screen.findByRole("button", { name: "اعطای دسترسی" }));
  await user.click(screen.getByRole("button", { name: "پایان" }));
  await user.click(screen.getByRole("button", { name: "انتخاب" }));
  await user.type(screen.getByLabelText("دلیل"), "retryable support action");
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));
  await user.click(screen.getByRole("button", { name: "ذخیره تغییرات" }));

  const calls = accessApi.grantUserAccess.mock.calls;
  expect(randomUUID).toHaveBeenCalledTimes(1);
  expect(calls).toHaveLength(2);
  expect(calls[0][1].client_idempotency_key).toBe("generated-grant-key");
  expect(calls[1][1].client_idempotency_key).toBe("generated-grant-key");
  expect(screen.queryByLabelText("کلید درخواست")).not.toBeInTheDocument();
});

it("warns before revoking paid access and sends a mandatory reason", async () => {
  const user = userEvent.setup();
  renderDetail();

  const grant = await screen.findByTestId("access-grant-subscription-grant");
  await user.click(within(grant).getByRole("button", { name: "قطع دسترسی" }));
  expect(screen.getByText("قطع دسترسی وضعیت مالی سفارش را Refund نمی‌کند.")).toBeInTheDocument();
  await user.type(screen.getByLabelText("دلیل قطع دسترسی"), "support correction");
  await user.click(screen.getByRole("button", { name: "تأیید قطع دسترسی" }));

  expect(accessApi.revokeUserAccess).toHaveBeenCalledWith("subscription-grant", "support correction");
});
