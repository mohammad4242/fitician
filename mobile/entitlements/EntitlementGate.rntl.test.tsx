import { fireEvent, render, screen } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
import { Text } from "react-native";
import { ApiError } from "@fitician/core";

jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("./EntitlementProvider", () => ({ useMobileEntitlements: jest.fn() }));

import { useMobileEntitlements } from "./EntitlementProvider";
import { EntitlementGate } from "./EntitlementGate";

const mockUseMobileEntitlements = jest.mocked(useMobileEntitlements);

test("renders children only when the capability is granted", () => {
  mockUseMobileEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: (code) => code === "training.plan.generate",
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry: jest.fn(),
    snapshot: null,
  });

  const { rerender } = render(
    <EntitlementGate entitlement="training.plan.generate">
      <Text>ساخت برنامه</Text>
    </EntitlementGate>,
  );
  expect(screen.getByText("ساخت برنامه")).toBeTruthy();

  mockUseMobileEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: () => false,
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry: jest.fn(),
    snapshot: null,
  });
  rerender(
    <EntitlementGate entitlement="training.plan.generate">
      <Text>ساخت برنامه</Text>
    </EntitlementGate>,
  );
  expect(screen.queryByText("ساخت برنامه")).toBeNull();
  expect(screen.getByText("این عملیات در دسترس نیست")).toBeTruthy();
});

test("renders the shared entitlement loading error and keeps retry available", () => {
  const retry = jest.fn();
  mockUseMobileEntitlements.mockReturnValue({
    error: new ApiError(503, "provider detail", null, "SERVICE_UNAVAILABLE", {
      requestId: "entitlement-corr-1",
    }),
    hasEntitlement: () => false,
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry,
    snapshot: null,
  });

  render(
    <EntitlementGate entitlement="training.plan.generate">
      <Text>ساخت برنامه</Text>
    </EntitlementGate>,
  );

  expect(screen.getByText("سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.")).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "تلاش دوباره" }));
  expect(retry).toHaveBeenCalledTimes(1);
});
