import { render, screen } from "@testing-library/react";
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
