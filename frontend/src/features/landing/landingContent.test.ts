import { expect, it } from "vitest";

import { landingScenes } from "./landingContent";

it("defines the three approved landing chapters", () => {
  expect(
    landingScenes.map(({ id, title, preload }) => ({ id, title, preload })),
  ).toEqual([
    { id: "strength", title: "از امروز، قوی‌تر.", preload: "metadata" },
    { id: "plan", title: "بدون حدس، با برنامه.", preload: "none" },
    { id: "progress", title: "هر تکرار، نزدیک‌تر.", preload: "none" },
  ]);
});

it("resolves landing videos through the public media resolver", () => {
  expect(landingScenes.map(({ videoSrc }) => videoSrc)).toEqual([
    "/media/landing/videos/hero-strength.mp4",
    "/media/landing/videos/plan-focus.mp4",
    "/media/landing/videos/progress-drive.mp4",
  ]);
});
