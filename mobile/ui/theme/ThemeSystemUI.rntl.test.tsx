import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { expect, jest, test } from "@jest/globals";
import { Appearance, Pressable } from "react-native";
import * as SecureStore from "expo-secure-store";
import * as SystemUI from "expo-system-ui";
import { StatusBar } from "expo-status-bar";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { ThemeSystemUI } from "./ThemeSystemUI";

jest.mock("expo-secure-store", () => ({ getItemAsync: jest.fn(), setItemAsync: jest.fn() }));
jest.mock("expo-system-ui", () => ({ setBackgroundColorAsync: jest.fn() }));
jest.mock("expo-status-bar", () => ({ StatusBar: jest.fn(() => null) }));
function Switch() {
  const { setTheme } = useTheme();
  return <Pressable accessibilityRole="button" accessibilityLabel="Light" onPress={() => setTheme("light")} />;
}
test("synchronizes explicit appearance with system controls, background and status bar", async () => {
  jest.mocked(SecureStore.getItemAsync).mockResolvedValue(null);
  jest.mocked(SecureStore.setItemAsync).mockResolvedValue();
  jest.mocked(SystemUI.setBackgroundColorAsync).mockResolvedValue();
  const scheme = jest.spyOn(Appearance, "setColorScheme").mockImplementation(() => {});
  render(<ThemeProvider><ThemeSystemUI /><Switch /></ThemeProvider>);
  expect(scheme).toHaveBeenLastCalledWith("dark");
  expect(StatusBar).toHaveBeenLastCalledWith({ style: "light" }, undefined);
  fireEvent.press(screen.getByRole("button", { name: "Light" }));
  await waitFor(() => expect(scheme).toHaveBeenLastCalledWith("light"));
  expect(SystemUI.setBackgroundColorAsync).toHaveBeenLastCalledWith("#f5faf8");
  expect(StatusBar).toHaveBeenLastCalledWith({ style: "dark" }, undefined);
  scheme.mockRestore();
});
