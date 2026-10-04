import { fireEvent, render, screen } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { Image, ScrollView, StyleSheet } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

jest.mock("expo-router", () => ({ useRouter: jest.fn() }));
import { useRouter } from "expo-router";
import PublicEntryScreen from "../app/(public)/index";

const mockPush = jest.fn();
beforeEach(() => {
  mockPush.mockClear();
  jest.mocked(useRouter).mockReturnValue({ push: mockPush } as never);
});

function renderEntry(bottom = 0, width = 360, height = 800) {
  return render(
    <SafeAreaProvider initialMetrics={{
      frame: { height, width, x: 0, y: 0 },
      insets: { bottom, left: 0, right: 0, top: 44 },
    }}>
      <PublicEntryScreen />
    </SafeAreaProvider>,
  );
}

test("renders the centered local welcome artwork without marketing or scroll UI", () => {
  renderEntry();
  const background = screen.getByTestId("public-entry-background");
  expect(background.props.source).toEqual(require("../assets/landing/pic_land.png"));
  expect(background.props.resizeMode).toBe("cover");
  expect(StyleSheet.flatten(background.props.style)).toMatchObject({
    width: "100%",
    height: "100%",
  });
  expect(screen.UNSAFE_getAllByType(Image)).toHaveLength(1);
  expect(screen.UNSAFE_queryByType(ScrollView)).toBeNull();
  for (const id of ["public-entry-film", "public-entry-process", "public-entry-meal-scan",
    "public-entry-body-analysis", "public-entry-menu", "signup-campaign-card"]) {
    expect(screen.queryByTestId(id)).toBeNull();
  }
  expect(screen.getAllByRole("button")).toHaveLength(2);
});

test("starts existing public onboarding", () => {
  renderEntry();
  fireEvent.press(screen.getByRole("button", { name: "شروع کنیم" }));
  expect(mockPush).toHaveBeenCalledWith("/public-onboarding");
});

test("shows the login prompt and opens existing sign-in", () => {
  renderEntry();
  expect(screen.getByText("حساب داری؟ ورود")).toBeTruthy();
  expect(screen.getByText("ورود")).toBeTruthy();
  fireEvent.press(screen.getByRole("button", { name: "ورود" }));
  expect(mockPush).toHaveBeenCalledWith("/auth/sign-in");
});

test.each([[360, 800, 24], [390, 844, 34], [412, 915, 24], [430, 932, 34]])(
  "keeps touch targets and safe-area clearance at %sx%s (bottom %s)",
  (width, height, bottom) => {
    renderEntry(bottom, width, height);
    const start = screen.getByTestId("public-entry-start");
    const login = screen.getByTestId("public-entry-sign-in");
    expect(StyleSheet.flatten(start.props.style)).toMatchObject({ minHeight: 60, width: "86%" });
    expect(StyleSheet.flatten(login.props.style).minHeight).toBeGreaterThanOrEqual(48);
    const area = screen.getByTestId("public-entry-actions");
    expect(StyleSheet.flatten(area.props.style).paddingBottom).toBe(bottom + 24);
    expect(StyleSheet.flatten(area.props.style).gap).toBe(16);
  },
);
