import { expect, it } from "vitest";

import { applyDesignSystem } from "./designSystem";

it("marks the document root as the Fitician application", () => {
  const documentElement = document.createElement("html");

  applyDesignSystem(documentElement);

  expect(documentElement).toHaveClass("fitician-app");
  expect(documentElement).toHaveAttribute("data-fitician-theme", "dark");
});
