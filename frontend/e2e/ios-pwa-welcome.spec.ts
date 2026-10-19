import { test, expect } from "@playwright/test";

for (const mode of ["safari", "display", "browser"] as const) {
  for (const size of [{ width: 320, height: 568 }, { width: 390, height: 844 }, { width: 430, height: 932 }, { width: 844, height: 390 }]) {
    test(`${mode} ${size.width}x${size.height}`, async ({ page }) => {
      await page.setViewportSize(size);
      await page.route("**/api/**", route => route.fulfill({ status: 401, contentType: "application/json", body: '{"detail":"Not authenticated"}' }));
      await page.addInitScript(mode => {
        // Both browser projects must emulate an iOS device for this iOS-only surface.
        Object.defineProperty(navigator, "userAgent", { value: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1" });
        if (mode === "safari") Object.defineProperty(navigator, "standalone", { value: true });
        if (mode === "display") {
          const original = window.matchMedia.bind(window);
          window.matchMedia = query => {
            const result = original(query);
            if (query === "(display-mode: standalone)") Object.defineProperty(result, "matches", { value: true });
            return result;
          };
        }
      }, mode);
      const errors: string[] = [];
      page.on("pageerror", error => errors.push(error.message));
      await page.goto("/");
      if (mode === "browser") {
        await expect(page.getByTestId("landing-film")).toBeAttached();
        await expect(page.locator(".landing-header")).toBeVisible();
        await expect(page.getByTestId("ios-pwa-welcome")).toHaveCount(0);
        expect(await page.evaluate(() => document.documentElement.scrollHeight > innerHeight)).toBe(true);
      } else {
        await expect(page.getByTestId("ios-pwa-welcome")).toBeVisible();
        const image = page.getByTestId("public-entry-background");
        await expect(image).toHaveJSProperty("complete", true);
        expect(await image.evaluate(i => (i as HTMLImageElement).naturalWidth)).toBeGreaterThan(0);
        await expect(image).toHaveCSS("object-fit", "cover");
        await expect(page.locator("video, header, nav, h1, h2, .signup-campaign-banner")).toHaveCount(0);
        await expect(page.getByRole("link")).toHaveCount(2);
        for (const link of await page.getByRole("link").all()) {
          const box = await link.boundingBox();
          expect(box!.y).toBeGreaterThanOrEqual(0);
          expect(box!.y + box!.height).toBeLessThanOrEqual(size.height);
        }
        expect(await page.evaluate(() => document.documentElement.scrollHeight)).toBe(size.height);
        await page.evaluate(() => scrollTo(0, 1000));
        expect(await page.evaluate(() => scrollY)).toBe(0);
        await expect(page.getByRole("link", { name: "شروع کنیم" })).toHaveAttribute("href", "/get-started");
        await expect(page.getByRole("link", { name: "حساب داری؟ ورود" })).toHaveAttribute("href", "/login");
        await page.screenshot({ path: `test-results/ios-pwa-welcome/${mode}-${size.width}.png` });
        if (size.width === 390) {
          await page.getByRole("link", { name: "شروع کنیم" }).click();
          await expect(page).toHaveURL(/\/get-started$/);
          await expect(page.locator(".ios-pwa-welcome")).toHaveCount(0);
          await expect(page.getByRole("heading", { name: "تو چه زمینه‌ای به کمک نیاز داری؟" })).toBeVisible();
          await page.waitForLoadState("load");
          await page.goto("/");
          await expect(page.getByTestId("ios-pwa-welcome")).toBeVisible();
          await expect(page.getByRole("link", { name: "حساب داری؟ ورود" })).toBeVisible();
          await page.getByRole("link", { name: "حساب داری؟ ورود" }).click();
          await expect(page).toHaveURL(/\/login$/);
          await expect(page.locator("#login-email")).toBeVisible();
        }
      }
      expect(errors).toEqual([]);
    });
  }
}

test("hides prerendered web content before application JavaScript runs", async ({ page }) => {
  await page.addInitScript(() => {
    Object.defineProperty(navigator, "userAgent", { value: "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 Mobile Safari/604.1" });
    Object.defineProperty(navigator, "standalone", { value: true });
  });
  await page.route("**/assets/*.js", route => route.abort());
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.locator("html")).toHaveAttribute("data-ios-pwa", "true");
  await expect(page.locator(".public-landing")).toBeHidden();
});
