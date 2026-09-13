import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, it, vi } from "vitest";

import { EntitlementGate } from "./EntitlementGate";

vi.mock("./EntitlementContext", () => ({
  useEntitlements: vi.fn(),
}));

import { useEntitlements } from "./EntitlementContext";

it("renders children only when the requested entitlement is present", () => {
  vi.mocked(useEntitlements).mockReturnValue({
    snapshot: null,
    loading: false,
    error: null,
    refresh: vi.fn(async () => undefined),
    retry: vi.fn(),
    hasEntitlement: (entitlement) => entitlement === "training.plan.generate",
    quotaFor: () => null,
  });

  const { rerender } = render(
    <EntitlementGate entitlement="training.plan.generate" fallback={<span>locked</span>}>
      <span>available</span>
    </EntitlementGate>,
  );
  expect(screen.getByText("available")).toBeInTheDocument();

  rerender(
    <EntitlementGate entitlement="nutrition.plan.generate" fallback={<span>locked</span>}>
      <span>available</span>
    </EntitlementGate>,
  );
  expect(screen.getByText("locked")).toBeInTheDocument();
});

it("links a locked feature to the matching plans paywall by default", () => {
  vi.mocked(useEntitlements).mockReturnValue({
    snapshot: null,
    loading: false,
    error: null,
    refresh: vi.fn(async () => undefined),
    retry: vi.fn(),
    hasEntitlement: () => false,
    quotaFor: () => null,
  });

  render(<MemoryRouter><EntitlementGate entitlement="body_analysis.run"><span>available</span></EntitlementGate></MemoryRouter>);

  expect(screen.getByRole("link", { name: "مشاهده پلن‌ها" })).toHaveAttribute(
    "href",
    "/plans?required=body_analysis.run",
  );
});
