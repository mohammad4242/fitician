/* oxlint-disable react/only-export-components -- provider and its hook form one public boundary */
import { createContext, useContext, useLayoutEffect, useState, type ReactNode } from "react";
import { applyDesignSystem } from "../styles/designSystem";

export type FiticianTheme = "dark" | "light";
export const THEME_STORAGE_KEY = "fitician.theme";
export function readTheme(): FiticianTheme {
  try { return localStorage.getItem(THEME_STORAGE_KEY) === "light" ? "light" : "dark"; }
  catch { return "dark"; }
}
const ThemeContext = createContext<{ theme: FiticianTheme; setTheme: (theme: FiticianTheme) => void } | null>(null);
export function ThemeProvider({ children }: { children: ReactNode }) {
  const [theme, updateTheme] = useState<FiticianTheme>(readTheme);
  useLayoutEffect(() => { applyDesignSystem(document.documentElement, theme); }, [theme]);
  function setTheme(value: FiticianTheme) {
    updateTheme(value);
    applyDesignSystem(document.documentElement, value);
    try { localStorage.setItem(THEME_STORAGE_KEY, value); } catch { /* Appearance still works without storage. */ }
  }
  return <ThemeContext.Provider value={{ theme, setTheme }}>{children}</ThemeContext.Provider>;
}
export function useTheme() {
  const context = useContext(ThemeContext);
  if (context === null) throw new Error("useTheme requires ThemeProvider");
  return context;
}
