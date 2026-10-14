import { fireEvent, render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { Image, ScrollView, StyleSheet } from "react-native";
import type { TransportRequest } from "@fitician/core";

jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
const mockPublicCampaignRequest = jest.fn<
  (request: TransportRequest) => Promise<null>
>();
jest.mock("../auth/MobileAuthProvider", () => ({
  useMobileAuth: () => ({ request: mockPublicCampaignRequest }),
}));

import { useRouter } from "expo-router";

import PublicEntryScreen from "../app/(public)/index";

const mockPush = jest.fn();
const mockUseRouter = jest.mocked(useRouter);

function renderEntry(bottom = 0, width = 360, height = 800) {
  return render(
    <SafeAreaProvider
      initialMetrics={{
        frame: { height, width, x: 0, y: 0 },
        insets: { bottom, left: 0, right: 0, top: 44 },
      }}
    >
      <PublicEntryScreen />
    </SafeAreaProvider>,
  );
}

beforeEach(() => {
  mockPush.mockClear();
  mockUseRouter.mockReturnValue({ push: mockPush } as never);
  mockPublicCampaignRequest.mockReset();
  mockPublicCampaignRequest.mockImplementation(() => new Promise<never>(() => undefined));
});

test("renders the original gym artwork as the Welcome background", () => {
  renderEntry();
  const background = screen.getByTestId("public-entry-background");
  expect(background.props.source).toEqual(require("../assets/landing/pic_land.jpg"));
  expect(background.props.resizeMode).toBe("cover");
  expect(StyleSheet.flatten(background.props.style)).toMatchObject({ width: "100%", height: "100%" });
  expect(screen.UNSAFE_getAllByType(Image)).toHaveLength(1);
  expect(screen.UNSAFE_queryByType(ScrollView)).toBeNull();
  expect(screen.queryByTestId("public-entry-film")).toBeNull();
  expect(screen.queryByTestId("public-entry-brand-mark")).toBeNull();
  expect(screen.getAllByRole("button")).toHaveLength(2);
  expect(mockPublicCampaignRequest).not.toHaveBeenCalled();
});

test("keeps native Welcome controls on the existing public routes", () => {
  renderEntry();
  fireEvent.press(screen.getByRole("button", { name: "شروع کنیم" }));
  fireEvent.press(screen.getByRole("button", { name: "ورود" }));
  expect(mockPush.mock.calls).toEqual([["/public-onboarding"], ["/auth/sign-in"]]);
});

test.each([[360, 800, 24], [390, 844, 34], [412, 915, 24], [430, 932, 34]])(
  "keeps Welcome controls reachable with safe-area clearance at %sx%s (bottom %s)",
  (width, height, bottom) => {
    renderEntry(bottom, width, height);
    expect(StyleSheet.flatten(screen.getByTestId("public-entry-start").props.style))
      .toMatchObject({ minHeight: 60, width: "86%" });
    expect(StyleSheet.flatten(screen.getByTestId("public-entry-sign-in").props.style).minHeight)
      .toBeGreaterThanOrEqual(48);
    expect(StyleSheet.flatten(screen.getByTestId("public-entry-actions").props.style).paddingBottom)
      .toBe(bottom + 24);
  },
);
