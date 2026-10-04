import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { expect, it } from "vitest";

it("bundles only the local welcome artwork for the native entry", async () => {
  const source = await readFile(resolve(import.meta.dirname, "PublicLandingScreen.tsx"), "utf8");
  expect(source).toContain('require("../assets/landing/pic_land.png")');
  expect(await readdir(resolve(import.meta.dirname, "../assets/landing"))).toEqual(["pic_land.png"]);
  expect(source).not.toMatch(/ScrollView|expo-video|reanimated|SignupCampaign|useMobileAuth|authCopy|BrandMark/);
  expect(source).toContain('backgroundColor: "#000000"');
});

it("preserves the guarded public route and existing onboarding and login destinations", async () => {
  const source = await readFile(resolve(import.meta.dirname, "PublicLandingScreen.tsx"), "utf8");
  const layout = await readFile(resolve(import.meta.dirname, "../app/(public)/_layout.tsx"), "utf8");
  expect(layout).toContain('<RouteGuard kind="public">');
  expect(source).toContain('router.push("/public-onboarding")');
  expect(source).toContain('router.push("/auth/sign-in")');
});
