import { useEffect } from "react";
import { Appearance } from "react-native";
import { StatusBar } from "expo-status-bar";
import * as SystemUI from "expo-system-ui";
import { useTheme } from "./ThemeProvider";

export function ThemeSystemUI() {
  const { theme, tokens } = useTheme();
  useEffect(() => {
    Appearance.setColorScheme(theme);
    void SystemUI.setBackgroundColorAsync(tokens.colors.canvas).catch(() => undefined);
  }, [theme, tokens]);
  return <StatusBar style={theme === "light" ? "dark" : "light"} />;
}
