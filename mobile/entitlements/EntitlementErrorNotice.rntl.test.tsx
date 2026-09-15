import { render, screen } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";

import { ApiError } from "@fitician/core";

jest.mock("expo-video", () => ({ VideoView: () => null, useVideoPlayer: () => ({}) }));
jest.mock("./EntitlementProvider", () => ({ useMobileEntitlements: jest.fn() }));

import { useMobileEntitlements } from "./EntitlementProvider";
import { EntitlementErrorNotice } from "./EntitlementErrorNotice";

const mockUseMobileEntitlements = jest.mocked(useMobileEntitlements);

test("renders a safe shared member message for entitlement loading failures", () => {
  mockUseMobileEntitlements.mockReturnValue({
    error: new ApiError(503, "database password", null, "SERVICE_UNAVAILABLE", {
      requestId: "member-entitlement-corr-1",
    }),
    hasEntitlement: () => false,
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry: jest.fn(),
    snapshot: null,
  });

  render(<EntitlementErrorNotice />);

  expect(screen.getByText("سرویس موقتاً در دسترس نیست. کمی بعد دوباره تلاش کنید.")).toBeTruthy();
  expect(screen.queryByText("database password")).toBeNull();
});

test("does not render when entitlements are healthy", () => {
  mockUseMobileEntitlements.mockReturnValue({
    error: null,
    hasEntitlement: () => true,
    loading: false,
    quotaFor: () => null,
    refresh: jest.fn(),
    retry: jest.fn(),
    snapshot: null,
  });

  render(<EntitlementErrorNotice />);

  expect(screen.queryByRole("alert")).toBeNull();
});
