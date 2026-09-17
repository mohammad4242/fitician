import { afterEach, expect, it, vi } from "vitest";

import { publicMediaPath, publicMediaUrl } from "./publicMedia";

afterEach(() => {
  vi.unstubAllEnvs();
});

it("uses the backend media path when no public base is configured", () => {
  expect(publicMediaUrl("public/landing/videos/story.mp4")).toBe(
    "/media/landing/videos/story.mp4",
  );
});

it("uses the configured public base without exposing provider logic to callers", () => {
  vi.stubEnv("VITE_MEDIA_PUBLIC_BASE_URL", "https://media.example.test/");

  expect(publicMediaUrl("public/landing/images/body.png")).toBe(
    "https://media.example.test/public/landing/images/body.png",
  );
});

it("rejects keys outside the public namespace", () => {
  expect(() => publicMediaUrl("private/body-photos/aa/photo.jpg")).toThrow(
    "public media object key",
  );
});

it("maps provider-neutral API media paths into the public resolver", () => {
  expect(publicMediaPath("/media/exercises/seed/cable-curl.gif")).toBe(
    "/media/exercises/seed/cable-curl.gif",
  );
  expect(publicMediaPath("/exercises/upper-body/chest/press.gif")).toBe(
    "/media/exercises/upper-body/chest/press.gif",
  );
  expect(publicMediaPath("/exercises/exercise-placeholder.svg")).toBe(
    "/exercises/exercise-placeholder.svg",
  );
});
