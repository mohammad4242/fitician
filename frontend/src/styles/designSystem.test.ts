import { expect, it } from "vitest";

import { applyDesignSystem } from "./designSystem";

it("marks the document root as the Fitician application", () => {
  const documentElement = document.createElement("html");

  applyDesignSystem(documentElement);

  expect(documentElement).toHaveClass("fitician-app");
  expect(documentElement).toHaveAttribute("data-fitician-theme", "dark");
});

it("applies explicit Light without overwriting it with Dark", () => {
  const root = document.createElement("html");
  applyDesignSystem(root, "light");
  expect(root.dataset.fiticianTheme).toBe("light");
  expect(root.style.colorScheme).toBe("light");
  applyDesignSystem(root, "dark");
  expect(root.style.colorScheme).toBe("dark");
});

it("defines readable semantic text and accent foregrounds in both CSS palettes", async () => {
  const { readFileSync } = await import("node:fs");
  const css = readFileSync("src/styles/tokens.css", "utf8");
  const luminance = (hex: string) => {
    const channels = hex.slice(1).match(/../g)!.map(v => parseInt(v, 16) / 255)
      .map(v => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722;
  };
  const contrast = (a: string, b: string) => {
    const l = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (l[0] + 0.05) / (l[1] + 0.05);
  };
  const dark = css.match(/:root, \[data-fitician-theme="dark"\] \{([^}]+)\}/)![1];
  const light = css.match(/\[data-fitician-theme="light"\] \{([^}]+)\}/)![1];
  const tokens = (block: string) => Object.fromEntries([...block.matchAll(/--fitician-([\w-]+): (#[\da-f]{6});/g)].map(m => [m[1], m[2]]));
  const shared = tokens(dark);
  for (const colors of [shared, { ...shared, ...tokens(light) }]) {
    for (const background of ["canvas", "surface", "surface-subtle", "surface-raised"]) {
      for (const foreground of ["ink", "muted", "placeholder", "accent-ink", "danger", "success", "amber"]) {
        expect(contrast(colors[foreground], colors[background]), `${foreground} on ${background}`).toBeGreaterThanOrEqual(4.5);
      }
    }
    expect(colors.aqua).toBe("#50dfce");
    expect(contrast(colors["on-accent"], colors.aqua)).toBeGreaterThanOrEqual(4.5);
    expect(contrast(colors["on-danger"], colors.danger)).toBeGreaterThanOrEqual(4.5);
  }
});
