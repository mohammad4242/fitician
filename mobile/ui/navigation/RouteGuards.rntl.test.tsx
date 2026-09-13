import { act, fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { Text } from "react-native";

jest.mock("expo-router", () => ({ Redirect: () => null }));
jest.mock("../../auth/MobileAuthProvider", () => ({ useMobileAuth: jest.fn() }));
jest.mock("../../platform/logging", () => ({ logDevelopmentDiagnostic: jest.fn() }));
jest.mock("../components", () => {
  const { Button, Text, View } = require("react-native") as typeof import("react-native");
  return {
    Notice: ({
      actionLabel,
      message,
      onAction,
      title,
    }: {
      actionLabel: string;
      message: string;
      onAction: () => void;
      title: string;
    }) => (
      <View>
        <Text>{title}</Text>
        <Text>{message}</Text>
        <Button title={actionLabel} onPress={onAction} />
      </View>
    ),
  };
});

import { useMobileAuth } from "../../auth/MobileAuthProvider";
import { MobileRouteStateProviderFromAuth, RouteGuard } from "./RouteGuards";

const mockUseMobileAuth = jest.mocked(useMobileAuth);

const user = {
  created_at: "2026-01-01T00:00:00Z",
  email: "member@example.com",
  id: "member-1",
  is_admin: false,
  phone_number: null,
};

beforeEach(() => {
  mockUseMobileAuth.mockReset();
});

test("shows a profile retry state and resumes the member route after retry", async () => {
  let profileAttempts = 0;
  const request = jest.fn(async (input: { path: string }) => {
    if (input.path === "/api/v1/profile/status") {
      profileAttempts += 1;
      if (profileAttempts === 1) throw new TypeError("Network request failed");
      return {
        completion_state: "both_ready",
        product_mode: "both",
        user_id: "member-1",
      };
    }
    return { authorized: false };
  });
  mockUseMobileAuth.mockReturnValue({
    request,
    status: "signed_in",
    user,
  } as never);

  render(
    <MobileRouteStateProviderFromAuth>
      <RouteGuard kind="member">
        <Text>member-content</Text>
      </RouteGuard>
    </MobileRouteStateProviderFromAuth>,
  );

  const retry = await screen.findByRole("button", { name: "دوباره تلاش کن" });
  expect(screen.queryByText("member-content")).toBeNull();

  await act(async () => {
    fireEvent.press(retry);
  });

  await waitFor(() => expect(screen.getByText("member-content")).toBeTruthy());
  expect(profileAttempts).toBe(2);
});

test("shows a specialist retry state and resumes the protected route after retry", async () => {
  let coachAttempts = 0;
  const request = jest.fn(async (input: { path: string }) => {
    if (input.path === "/api/v1/profile/status") {
      return {
        completion_state: "both_ready",
        product_mode: "both",
        user_id: "member-1",
      };
    }
    if (input.path === "/api/v1/coach/workout-reviews/access") {
      coachAttempts += 1;
      if (coachAttempts === 1) throw new TypeError("Network request failed");
      return { authorized: true };
    }
    return { authorized: false };
  });
  mockUseMobileAuth.mockReturnValue({
    request,
    status: "signed_in",
    user,
  } as never);

  render(
    <MobileRouteStateProviderFromAuth>
      <RouteGuard kind="coach">
        <Text>coach-content</Text>
      </RouteGuard>
    </MobileRouteStateProviderFromAuth>,
  );

  const retry = await screen.findByRole("button", { name: "دوباره تلاش کن" });
  expect(screen.queryByText("coach-content")).toBeNull();

  await act(async () => {
    fireEvent.press(retry);
  });

  await waitFor(() => expect(screen.getByText("coach-content")).toBeTruthy());
  expect(coachAttempts).toBe(2);
});

test("persists the device timezone once for each signed-in user", async () => {
  const timezoneUpdates: Array<{ timezone: string; userId: string }> = [];
  const request = jest.fn(async (input: { body?: { timezone?: string }; path: string }) => {
    if (input.path === "/api/v1/profile/status") {
      return {
        completion_state: "both_ready",
        product_mode: "both",
        user_id: "member-1",
      };
    }
    if (input.path === "/api/v1/profile/timezone") {
      timezoneUpdates.push({ timezone: input.body?.timezone ?? "", userId: "member-1" });
      return { timezone: input.body?.timezone };
    }
    return { authorized: false };
  });
  mockUseMobileAuth.mockReturnValue({
    request,
    status: "signed_in",
    user,
  } as never);

  const view = render(
    <MobileRouteStateProviderFromAuth>
      <RouteGuard kind="member">
        <Text>member-content</Text>
      </RouteGuard>
    </MobileRouteStateProviderFromAuth>,
  );

  await waitFor(() => expect(timezoneUpdates).toHaveLength(1));
  expect(timezoneUpdates[0]?.timezone).toBeTruthy();

  view.rerender(
    <MobileRouteStateProviderFromAuth>
      <RouteGuard kind="member">
        <Text>member-content</Text>
      </RouteGuard>
    </MobileRouteStateProviderFromAuth>,
  );
  await waitFor(() => expect(timezoneUpdates).toHaveLength(1));
});

test("retries timezone persistence when the authenticated identity changes", async () => {
  const firstRequest = jest.fn(async (input: { path: string }) => {
    if (input.path === "/api/v1/profile/status") {
      return {
        completion_state: "both_ready",
        product_mode: "both",
        user_id: "member-1",
      };
    }
    if (input.path === "/api/v1/profile/timezone") return { timezone: "UTC" };
    return { authorized: false };
  });
  const secondRequest = jest.fn(async (input: { path: string }) => {
    if (input.path === "/api/v1/profile/status") {
      return {
        completion_state: "both_ready",
        product_mode: "both",
        user_id: "member-2",
      };
    }
    if (input.path === "/api/v1/profile/timezone") return { timezone: "UTC" };
    return { authorized: false };
  });
  mockUseMobileAuth.mockReturnValue({
    request: firstRequest,
    status: "signed_in",
    user,
  } as never);

  const view = render(
    <MobileRouteStateProviderFromAuth>
      <RouteGuard kind="member">
        <Text>member-content</Text>
      </RouteGuard>
    </MobileRouteStateProviderFromAuth>,
  );
  await waitFor(() => expect(firstRequest).toHaveBeenCalledWith(expect.objectContaining({
    path: "/api/v1/profile/timezone",
  })));

  mockUseMobileAuth.mockReturnValue({
    request: secondRequest,
    status: "signed_in",
    user: { ...user, id: "member-2" },
  } as never);
  view.rerender(
    <MobileRouteStateProviderFromAuth>
      <RouteGuard kind="member">
        <Text>member-content</Text>
      </RouteGuard>
    </MobileRouteStateProviderFromAuth>,
  );

  await waitFor(() => expect(secondRequest).toHaveBeenCalledWith(expect.objectContaining({
    path: "/api/v1/profile/timezone",
  })));
});
