import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, expect, it, vi } from "vitest";
import { ThemeProvider, useTheme } from "./ThemeProvider";

function Control() {
  const { theme, setTheme } = useTheme();
  return <button onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>{theme}</button>;
}
beforeEach(() => { localStorage.clear(); document.documentElement.removeAttribute("data-fitician-theme"); });
it.each([null, "invalid", "system"])("defaults to Dark for %s", (stored) => {
  if (stored) localStorage.setItem("fitician.theme", stored);
  render(<ThemeProvider><Control /></ThemeProvider>);
  expect(screen.getByRole("button")).toHaveTextContent("dark");
  expect(document.documentElement).toHaveAttribute("data-fitician-theme", "dark");
  expect(document.documentElement.style.colorScheme).toBe("dark");
});
it("restores Light and switches both ways immediately with persisted chrome", () => {
  localStorage.setItem("fitician.theme", "light");
  const meta = document.createElement("meta"); meta.name = "theme-color"; document.head.append(meta);
  const view = render(<ThemeProvider><Control /></ThemeProvider>);
  expect(screen.getByRole("button")).toHaveTextContent("light");
  expect(document.documentElement.dataset.fiticianTheme).toBe("light");
  expect(document.documentElement.style.colorScheme).toBe("light");
  expect(meta.content).toBe("#f5faf8");
  fireEvent.click(screen.getByRole("button"));
  expect(localStorage.getItem("fitician.theme")).toBe("dark");
  expect(meta.content).toBe("#020607");
  expect(document.documentElement.style.backgroundColor).toBe("rgb(2, 6, 7)");
  fireEvent.click(screen.getByRole("button"));
  expect(localStorage.getItem("fitician.theme")).toBe("light");
  view.unmount(); render(<ThemeProvider><Control /></ThemeProvider>);
  expect(screen.getByRole("button")).toHaveTextContent("light"); meta.remove();
});
it("switches when storage is unavailable", () => {
  vi.spyOn(Storage.prototype, "setItem").mockImplementationOnce(() => { throw new Error("blocked"); });
  render(<ThemeProvider><Control /></ThemeProvider>);
  fireEvent.click(screen.getByRole("button"));
  expect(document.documentElement.dataset.fiticianTheme).toBe("light");
});
