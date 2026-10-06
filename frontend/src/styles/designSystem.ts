import type { FiticianTheme } from "../theme/ThemeProvider";

export function applyDesignSystem(documentElement: HTMLElement, theme: FiticianTheme = "dark") {
  documentElement.classList.add("fitician-app");
  documentElement.dataset.fiticianTheme = theme;
  documentElement.style.colorScheme = theme;
  documentElement.style.backgroundColor = theme === "light" ? "#f5faf8" : "#020607";
  documentElement.ownerDocument.querySelector<HTMLMetaElement>('meta[name="theme-color"]')
    ?.setAttribute("content", theme === "light" ? "#f5faf8" : "#020607");
}
