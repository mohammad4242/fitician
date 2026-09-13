import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { Pressable, Text } from "react-native";
import type { EntitlementSnapshot } from "@fitician/core/entitlements";

jest.mock("../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("./entitlementApi", () => ({ createEntitlementApi: jest.fn() }));

import { useMobileAuth } from "../auth/MobileAuthProvider";
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
      <Text>{state.hasEntitlement("training.coach_review") ? "allowed" : "denied"}</Text>
      <Pressable accessibilityRole="button" onPress={state.refresh}><Text>refresh</Text></Pressable>
    </>
  );
}

let authState: { readonly status: "signed_in" | "signed_out"; readonly user: { readonly id: string } | null };

beforeEach(() => {
  authState = { status: "signed_in", user: { id: "member-1" } };
  mockGetSnapshot.mockReset();
  mockGetSnapshot.mockResolvedValue(snapshot);
  mockCreateEntitlementApi.mockReturnValue({
    getProducts: jest.fn(),
    getSnapshot: mockGetSnapshot,
  } as never);
  mockUseMobileAuth.mockImplementation(() => ({
    request: jest.fn(),
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
