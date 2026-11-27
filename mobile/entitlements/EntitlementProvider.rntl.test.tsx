import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { AppState, Pressable, Text } from "react-native";
import type { EntitlementSnapshot } from "@fitician/core/entitlements";

jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../billing/billingApi", () => ({ createBillingApi: jest.fn() }));
jest.mock("./entitlementApi", () => ({ createEntitlementApi: jest.fn() }));

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { createBillingApi } from "../billing/billingApi";
import { createEntitlementApi } from "./entitlementApi";
import { EntitlementProvider, useMobileEntitlements } from "./EntitlementProvider";

const mockUseMobileAuth = jest.mocked(useMobileAuth);
const mockCreateEntitlementApi = jest.mocked(createEntitlementApi);
const mockGetSnapshot = jest.fn<() => Promise<EntitlementSnapshot>>();

const snapshot = {
  active_packages: ["training_coach"],
  entitlements: {
    granted: ["training.plan.generate", "training.coach_review"],
    quotas: [],
  },
  grants: [],
  primary_package: "training_coach",
  trial: { active: false, ends_at: null },
} as const;

function Consumer() {
  const state = useMobileEntitlements();
  return (
    <>
      <Text>{state.snapshot?.primary_package ?? "empty"}</Text>
      <Text>{state.paymentStatus ?? "no-payment"}</Text>
      <Text>{state.hasEntitlement("training.coach_review") ? "allowed" : "denied"}</Text>
      <Pressable accessibilityRole="button" onPress={state.refresh}><Text>refresh</Text></Pressable>
    </>
  );
}

const stableRequest = jest.fn();
let authState: { readonly status: "signed_in" | "signed_out"; readonly user: { readonly id: string } | null };

beforeEach(() => {
  authState = { status: "signed_in", user: { id: "member-1" } };
  jest.mocked(createBillingApi).mockReturnValue({getPendingCheckouts: jest.fn<() => Promise<unknown[]>>().mockResolvedValue([])} as never);
  mockGetSnapshot.mockReset();
  mockGetSnapshot.mockResolvedValue(snapshot);
  mockCreateEntitlementApi.mockReturnValue({
    getProducts: jest.fn(),
    getSnapshot: mockGetSnapshot,
  } as never);
  mockUseMobileAuth.mockImplementation(() => ({
    request: stableRequest,
    status: authState.status,
    user: authState.user,
  } as never));
});

test("loads once for the signed-in member and exposes capability helpers", async () => {
  render(
    <EntitlementProvider>
      <Consumer />
    </EntitlementProvider>,
  );

  expect(await screen.findByText("training_coach")).toBeTruthy();
  expect(screen.getByText("allowed")).toBeTruthy();
  expect(mockGetSnapshot).toHaveBeenCalledTimes(1);
});

test("clears access after sign out", async () => {
  const rendered = render(
    <EntitlementProvider>
      <Consumer />
    </EntitlementProvider>,
  );
  await screen.findByText("training_coach");

  authState = { status: "signed_out", user: null };
  rendered.rerender(
    <EntitlementProvider>
      <Consumer />
    </EntitlementProvider>,
  );

  await waitFor(() => expect(screen.getByText("empty")).toBeTruthy());
  expect(screen.getByText("denied")).toBeTruthy();
});

test("refreshes the snapshot after a verified purchase", async () => {
  render(
    <EntitlementProvider>
      <Consumer />
    </EntitlementProvider>,
  );
  await screen.findByText("training_coach");

  fireEvent.press(screen.getByRole("button", { name: "refresh" }));

  await waitFor(() => expect(mockGetSnapshot).toHaveBeenCalledTimes(2));
});

test("recovers a pending payment on startup and refreshes access", async () => {
  const verifyPayment = jest.fn<() => Promise<{verified: boolean}>>().mockResolvedValue({verified: true});
  jest.mocked(createBillingApi).mockReturnValue({
    getPendingCheckouts: jest.fn<() => Promise<unknown[]>>().mockResolvedValue([
      {provider: "tetrapay", transaction_id: "tx-1", provider_reference: "token"},
    ]), verifyPayment,
  } as never);
  render(<EntitlementProvider><Consumer /></EntitlementProvider>);
  await waitFor(() => expect(verifyPayment).toHaveBeenCalledWith("tetrapay", {transaction_id: "tx-1"}));
  await waitFor(() => expect(mockGetSnapshot.mock.calls.length).toBeGreaterThanOrEqual(2));
  expect(screen.getByText("verified")).toBeTruthy();
});

test("refreshes server entitlements on resume when the scheduler already settled payment", async () => {
  const listener = jest.spyOn(AppState, "addEventListener");
  render(<EntitlementProvider><Consumer /></EntitlementProvider>);
  await screen.findByText("training_coach");
  const resume = listener.mock.calls.at(-1)?.[1];
  await act(async () => { resume?.("active"); });
  await waitFor(() => expect(mockGetSnapshot.mock.calls.length).toBeGreaterThanOrEqual(2));
  listener.mockRestore();
});
