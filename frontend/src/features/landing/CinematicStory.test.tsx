import { render, screen } from "@testing-library/react";
import { renderToString } from "react-dom/server";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";

import androidGymImage from "../../../../mobile/assets/landing/pic_land.jpg";
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
  ["iPhone", false, true, "", 0],
  ["iPhone", true, false, "", 0],
  ["iPad", false, true, "", 0],
  ["Macintosh", false, true, "MacIntel", 5],
])("uses the exact Android image in installed iOS: %s %s %s", (agent, safari, display, platform, touches) => {
  environment(agent, safari, display, platform, touches);
  render(<MemoryRouter><CinematicStory reducedMotion={false} /></MemoryRouter>);

  expect(screen.queryByTestId("landing-film")).not.toBeInTheDocument();
  expect(screen.getByTestId("landing-gym-image")).toHaveAttribute("src", androidGymImage);
  expect(screen.getByTestId("landing-gym-image")).toHaveAttribute("alt", "");
  expect(screen.getAllByRole("link")[0]).toHaveAttribute("href", "/get-started");
});

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

it("supports Safari standalone when matchMedia is unavailable", () => {
  environment("iPhone", true, false);
  vi.stubGlobal("matchMedia", undefined);
  render(<MemoryRouter><CinematicStory reducedMotion={false} /></MemoryRouter>);
  expect(screen.getByTestId("landing-gym-image")).toHaveAttribute("src", androidGymImage);
  expect(screen.queryByTestId("landing-film")).not.toBeInTheDocument();
});
