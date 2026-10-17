import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import { CinematicStory } from "./CinematicStory";

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function environment(userAgent: string, standalone: boolean, displayMode: boolean, platform = "", touches = 0) {
  vi.stubGlobal("navigator", { userAgent, platform, maxTouchPoints: touches, standalone });
  vi.stubGlobal("matchMedia", vi.fn((query: string) => ({
    matches: query === "(display-mode: standalone)" && displayMode,
  })));
}

it.each([
  ["iPhone", false],
  ["iPad", false],
  ["Chrome Android", false],
  ["Chrome Android", true],
  ["Macintosh", false],
  ["Macintosh", true],
])("preserves the Web film for %s, standalone %s", (agent, standalone) => {
  environment(agent, standalone, standalone);
  render(<MemoryRouter><CinematicStory reducedMotion={false} /></MemoryRouter>);

  const film = screen.getByTestId("landing-film");
  expect(film).toHaveAttribute("src", expect.stringContaining("/landing/videos/landfilm.mp4"));
  expect(film).toHaveAttribute("autoplay");
  expect(film).toHaveProperty("muted", true);
  expect(film).toHaveAttribute("playsinline");
  expect(film).toHaveAttribute("loop");
  expect(film).toHaveAttribute("preload", "metadata");
  expect(screen.queryByTestId("landing-gym-image")).not.toBeInTheDocument();
});

it("keeps the prerendered markup stable for hydration", () => {
  environment("iPhone", true, true);
  const html = renderToString(<MemoryRouter><CinematicStory reducedMotion={false} /></MemoryRouter>);
  expect(html).toContain('data-testid="landing-film"');
  expect(html).not.toContain('data-testid="landing-gym-image"');
});

it("keeps reduced-motion video behavior in Safari tabs", () => {
  environment("iPhone", false, false);
  render(<MemoryRouter><CinematicStory reducedMotion /></MemoryRouter>);
  expect(screen.getByTestId("landing-film")).not.toHaveAttribute("autoplay");
});
