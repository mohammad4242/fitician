/* oxlint-disable react/only-export-components -- provider and its hooks form one public boundary */
import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import * as SecureStore from "expo-secure-store";
import { getThemeTokens, type FiticianTheme, type FiticianTokens } from "../tokens";

export const THEME_STORAGE_KEY = "fitician.appearance-theme";
const defaultTheme = { theme: "dark" as FiticianTheme, tokens: getThemeTokens("dark"), setTheme: (_theme: FiticianTheme) => {} };
const ThemeContext = createContext(defaultTheme);
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, updateTheme] = useState<FiticianTheme>("dark");
  const selected = useRef(false);
  const writes = useRef(Promise.resolve());
  useEffect(() => {
    let active = true;
    void SecureStore.getItemAsync(THEME_STORAGE_KEY).then(value => {
      if (active && !selected.current) updateTheme(value === "light" ? "light" : "dark");
    }).catch(() => undefined);
    return () => { active = false; };
  }, []);
  const value = useMemo(() => ({
    theme,
    tokens: getThemeTokens(theme),
    setTheme: (next: FiticianTheme) => {
      selected.current = true;
      updateTheme(next);
      // Serialize rapid selections so the final stored choice always matches the UI.
      writes.current = writes.current.then(() => SecureStore.setItemAsync(THEME_STORAGE_KEY, next)).catch(() => undefined);
    },
  }), [theme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}
export function useTheme() { return useContext(ThemeContext); }
export function useThemeTokens(): FiticianTokens { return useTheme().tokens; }
export function useThemeStyles<T>(factory: (tokens: FiticianTokens) => T): T {
  const tokens = useThemeTokens();
  return useMemo(() => factory(tokens), [factory, tokens]);
}
