import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, it } from "vitest";

it("bundles the exact uploaded gym image on the public Welcome route", async () => {
  const source = await readFile(resolve(import.meta.dirname, "PublicLandingScreen.tsx"), "utf8");
  expect(source).toContain('require("../assets/landing/pic_land.jpg")');
  const bytes = await readFile(resolve(import.meta.dirname, "../assets/landing/pic_land.jpg"));
  expect(createHash("sha256").update(bytes).digest("hex"))
    .toBe("92e8977e4d62f13699b70c82aa4d600a16eece4de6a33f020d2eedbe370398fe");
});

it("retains public route guards and native Welcome actions", async () => {
  const source = await readFile(resolve(import.meta.dirname, "PublicLandingScreen.tsx"), "utf8");
  const layout = await readFile(resolve(import.meta.dirname, "../app/(public)/_layout.tsx"), "utf8");
  expect(layout).toContain('<RouteGuard kind="public">');
  expect(source).toContain('router.push("/public-onboarding")');
  expect(source).toContain('router.push("/auth/sign-in")');
  expect(source).not.toContain("landfilm");
  expect(source).not.toContain("Animated.ScrollView");
});
