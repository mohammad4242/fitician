import { act, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import * as auth from "../auth/AuthContext";
import * as api from "./api";
import { EntitlementProvider, useEntitlements } from "./EntitlementContext";

const snapshot = {
  primary_package: "training" as const,
  active_packages: ["training" as const],
  trial: { active: false, ends_at: null },
  entitlements: {
    granted: ["training.plan.generate" as const],
    quotas: [{
      entitlement: "body_analysis.run" as const,
      limit: 1,
      used: 0,
      remaining: 1,
      window_days: 7,
      reset_at: "2026-09-20T00:00:00Z",
    }],
  },
  grants: [],
};

const authUser = {
  id: "user-1",
  email: "member@example.com",
  phone_number: null,
  created_at: "2026-09-13T00:00:00Z",
  is_admin: false,
};

function Probe() {
  const { snapshot: current, loading, error, retry, refresh, hasEntitlement, quotaFor } = useEntitlements();
  return (
    <div>
      <span>{loading ? "loading" : error ? "error" : current?.primary_package ?? "empty"}</span>
      <span>{hasEntitlement("training.plan.generate") ? "can-generate" : "locked"}</span>
      <span>{quotaFor("body_analysis.run")?.remaining ?? "no-quota"}</span>
      <button type="button" onClick={retry}>retry</button>
      <button type="button" onClick={() => void refresh()}>refresh</button>
    </div>
  );
}

afterEach(() => vi.restoreAllMocks());

it("loads once per signed-in user and exposes capability/quota helpers", async () => {
  vi.spyOn(auth, "useAuth").mockReturnValue({ user: authUser } as ReturnType<typeof auth.useAuth>);
  const getSnapshot = vi.spyOn(api, "getEntitlementSnapshot").mockResolvedValue(snapshot);

  render(
    <EntitlementProvider>
      <Probe />
    </EntitlementProvider>,
  );

  await waitFor(() => expect(screen.getByText("training")).toBeInTheDocument());
  expect(screen.getByText("can-generate")).toBeInTheDocument();
  expect(screen.getByText("1")).toBeInTheDocument();
  expect(getSnapshot).toHaveBeenCalledTimes(1);
});

it("clears the snapshot after logout", async () => {
  let currentUser: typeof authUser | null = authUser;
  vi.spyOn(auth, "useAuth").mockImplementation(() => ({ user: currentUser } as ReturnType<typeof auth.useAuth>));
  vi.spyOn(api, "getEntitlementSnapshot").mockResolvedValue(snapshot);
  const { rerender } = render(
    <EntitlementProvider>
      <Probe />
    </EntitlementProvider>,
  );
  await waitFor(() => expect(screen.getByText("training")).toBeInTheDocument());

  await act(async () => {
    currentUser = null;
    rerender(
      <EntitlementProvider>
        <Probe />
      </EntitlementProvider>,
    );
  });

  expect(screen.getByText("empty")).toBeInTheDocument();
  expect(screen.getByText("locked")).toBeInTheDocument();
});

it("retries a failed snapshot request", async () => {
  vi.spyOn(auth, "useAuth").mockReturnValue({ user: authUser } as ReturnType<typeof auth.useAuth>);
  const getSnapshot = vi.spyOn(api, "getEntitlementSnapshot")
    .mockRejectedValueOnce(new Error("offline"))
    .mockResolvedValueOnce(snapshot);

  const user = render(
    <EntitlementProvider>
      <Probe />
    </EntitlementProvider>,
  );
  await waitFor(() => expect(screen.getByText("error")).toBeInTheDocument());

  await act(async () => {
    screen.getByRole("button", { name: "retry" }).click();
  });
  await waitFor(() => expect(screen.getByText("training")).toBeInTheDocument());
  expect(getSnapshot).toHaveBeenCalledTimes(2);
  user.unmount();
});

it("exposes an explicit async refresh for post-purchase access updates", async () => {
  vi.spyOn(auth, "useAuth").mockReturnValue({ user: authUser } as ReturnType<typeof auth.useAuth>);
  const getSnapshot = vi.spyOn(api, "getEntitlementSnapshot").mockResolvedValue(snapshot);

  render(
    <EntitlementProvider>
      <Probe />
    </EntitlementProvider>,
  );
  await waitFor(() => expect(screen.getByText("training")).toBeInTheDocument());

  await act(async () => {
    screen.getByRole("button", { name: "refresh" }).click();
  });

  await waitFor(() => expect(getSnapshot).toHaveBeenCalledTimes(2));
  expect(screen.getByText("training")).toBeInTheDocument();
});
