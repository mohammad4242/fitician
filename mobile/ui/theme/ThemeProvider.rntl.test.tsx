import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { beforeEach, expect, jest, test } from "@jest/globals";
import { Pressable, Text } from "react-native";
import * as SecureStore from "expo-secure-store";
import { ThemeProvider, useTheme } from "./ThemeProvider";
import { Card } from "../components/Card";
import { Button } from "../components/Button";
import { TextField } from "../components/Input";
import { SegmentedControl } from "../components/SegmentedControl";

jest.mock("expo-secure-store", () => ({ getItemAsync: jest.fn(), setItemAsync: jest.fn() }));
function Control() {
  const { theme, setTheme, tokens } = useTheme();
  return <Card testID="card"><Text testID="ink" style={{ color: tokens.colors.ink }}>{theme}</Text><Pressable accessibilityRole="button" accessibilityLabel="switch" onPress={() => setTheme(theme === "dark" ? "light" : "dark")} /><Button label="Aqua" /><TextField accessibilityLabel="Name" label="Name" /><SegmentedControl variant="filled" selectedValue={theme} options={[{ label: "Dark", value: "dark" }, { label: "Light", value: "light" }]} onChange={value => setTheme(value === "light" ? "light" : "dark")} /></Card>;
}
beforeEach(() => { jest.mocked(SecureStore.getItemAsync).mockReset().mockResolvedValue(null); jest.mocked(SecureStore.setItemAsync).mockReset().mockResolvedValue(); });
test("defaults Dark and updates mounted shared components both ways", async () => {
  render(<ThemeProvider><Control /></ThemeProvider>);
  await waitFor(() => expect(screen.getByText("dark")).toBeTruthy());
  expect(screen.getByTestId("card")).toHaveStyle({ backgroundColor: "#081211" });
  fireEvent.press(screen.getByRole("button", { name: "switch" }));
  expect(screen.getByTestId("card")).toHaveStyle({ backgroundColor: "#ffffff" });
  expect(screen.getByTestId("ink")).toHaveStyle({ color: "#102422" });
  expect(screen.getByText("Aqua")).toHaveStyle({ color: "#020607" });
  expect(screen.getByLabelText("Name")).toHaveStyle({ color: "#102422", backgroundColor: "#ffffff" });
  expect(screen.getByRole("radio", { name: "Light" })).toHaveStyle({ backgroundColor: "#50dfce" });
  await waitFor(() => expect(SecureStore.setItemAsync).toHaveBeenCalledWith("fitician.appearance-theme", "light"));
  fireEvent.press(screen.getByRole("button", { name: "switch" }));
  expect(screen.getByTestId("card")).toHaveStyle({ backgroundColor: "#081211" });
  await waitFor(() => expect(SecureStore.setItemAsync).toHaveBeenLastCalledWith("fitician.appearance-theme", "dark"));
});
test("restores saved Light", async () => {
  jest.mocked(SecureStore.getItemAsync).mockResolvedValue("light");
  render(<ThemeProvider><Control /></ThemeProvider>);
  await waitFor(() => expect(screen.getByText("light")).toBeTruthy());
  expect(screen.getByTestId("card")).toHaveStyle({ backgroundColor: "#ffffff" });
  expect(SecureStore.setItemAsync).not.toHaveBeenCalled();
});
test("late storage read cannot override a new selection", async () => {
  let resolve!: (value: string) => void;
  jest.mocked(SecureStore.getItemAsync).mockReturnValue(new Promise<string>(done => { resolve = done; }));
  render(<ThemeProvider><Control /></ThemeProvider>);
  fireEvent.press(screen.getByRole("button", { name: "switch" }));
  resolve("dark");
  await waitFor(() => expect(screen.getByText("light")).toBeTruthy());
});

test.each(["invalid", "system", ""])("rejects invalid stored theme %s", async stored => {
  jest.mocked(SecureStore.getItemAsync).mockResolvedValue(stored);
  render(<ThemeProvider><Control /></ThemeProvider>);
  await waitFor(() => expect(screen.getByText("dark")).toBeTruthy());
});
test("keeps appearance responsive when storage fails", async () => {
  jest.mocked(SecureStore.getItemAsync).mockRejectedValue(new Error("unavailable"));
  jest.mocked(SecureStore.setItemAsync).mockRejectedValue(new Error("unavailable"));
  render(<ThemeProvider><Control /></ThemeProvider>);
  fireEvent.press(screen.getByRole("button", { name: "switch" }));
  await waitFor(() => expect(screen.getByText("light")).toBeTruthy());
});
