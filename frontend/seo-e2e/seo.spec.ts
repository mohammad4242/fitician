import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { expect, test } from "@playwright/test";
import { publicPaths, resolveSeo, pages } from "../src/seo/registry";

test("all canonical pages arrive with content, metadata and Persian RTL before JS", async ({ request }) => {
  for (const path of publicPaths()) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(200);
    const html = await response.text();
    expect(html).toContain('<html lang="fa" dir="rtl">');
    expect(html).toContain("<h1");
    expect(html).toContain('name="description"');
    expect(html).toContain(`href="${resolveSeo(path).canonical}"`);
    expect(html).toContain('name="robots" content="index, follow"');
    expect(html).toContain('application/ld+json');
    expect(html.match(/<title(?:\s[^>]*)?>/g)).toHaveLength(1);
  }
});
test("robots and sitemap expose only public canonical URLs", async ({ request }) => {
  expect(await (await request.get("/robots.txt")).text()).toContain("Sitemap: https://fitician.fit/sitemap.xml");
  const index = await (await request.get("/sitemap.xml")).text();
  expect(index).toContain("<sitemapindex");
  const sitemap = await (await request.get("/sitemap-1.xml")).text();
  expect(sitemap).toContain("/exercise-library/dumbbell-bench-press</loc>");
  expect(sitemap).toContain("/tools/bmi-calculator</loc>");
  expect(sitemap).not.toContain("/dashboard");
  expect(sitemap).not.toContain("/get-started");
});
test("nginx keeps member deep links and returns true 404s", async ({ request }) => {
  for (const path of ["/dashboard", "/workout-plan", "/exercises/", "/exercises/dumbbell-bench-press", "/body-progress/new", "/admin/support", "/get-started"]) {
    const response = await request.get(path);
    expect(response.status()).toBe(200);
    expect(response.headers()["x-robots-tag"]).toBe("noindex, follow");
    expect(await response.text()).toContain('name="robots" content="noindex, follow"');
  }
  for (const path of ["/unknown", "/dashboard/unknown", "/exercise-library/unknown", "/tools/unknown", "/assets/missing.js", "/media/missing.gif", "/api/missing", "/nginx-member-routes.conf", "/fitician_1000_profiles_audit_report.html", "/workout_engine_11_profiles.html"]) {
    const response = await request.get(path);
    expect(response.status(), path).toBe(404);
  }
});
test("public tools hydrate, calculate locally and remain responsive", async ({ page }) => {
  const errors: string[] = [];
  const requests: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("request", request => requests.push(request.url()));
  await page.goto("/tools/calorie-calculator");
  await page.getByRole("button", { name: "محاسبه نتیجه", exact: true }).click();
  await expect(page.locator("output")).toContainText("1,979");
  await expect(page).toHaveTitle(resolveSeo("/tools/calorie-calculator").title);
  expect(await page.locator('meta[name="description"]').count()).toBe(1);
  expect(await page.locator('link[rel="canonical"]').count()).toBe(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("link", { name: "محاسبه پروتئین روزانه برای افراد فعال", exact: true }).click();
  await page.getByRole("button", { name: "محاسبه نتیجه", exact: true }).click();
  await expect(page.locator("output")).toContainText("98 – 140");
  await page.locator('.tool-switcher a[href="/tools/bmi-calculator"]').click();
  await page.getByLabel("قد", { exact: true }).fill("۱۷۵");
  await page.getByLabel("وزن", { exact: true }).fill("۷۰");
  const calculationRequests: string[] = [];
  page.on("request", request => calculationRequests.push(request.url()));
  await page.getByRole("button", { name: "محاسبه نتیجه", exact: true }).click();
  await expect(page.locator("output")).toContainText("22.9");
  await expect(page.locator("output")).toContainText("بازه میانی مرجع");
  await expect(page).toHaveTitle(resolveSeo("/tools/bmi-calculator").title);
  await page.getByLabel("قد", { exact: true }).fill("0");
  await page.getByRole("button", { name: "محاسبه نتیجه", exact: true }).click();
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByLabel("قد", { exact: true })).toBeFocused();
  await expect(page.locator("output")).not.toContainText("22.9");
  expect(calculationRequests).toEqual([]);
  expect(requests.filter(url => /\/api\/|\.mp4|mediapipe|landfilm|body1/.test(url))).toEqual([]);
  expect(errors).toEqual([]);
});
test("exercise instructions and crawlable contextual links survive hydration", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/exercise-library/dumbbell-bench-press");
  await expect(page.getByRole("heading", { level: 1 })).toContainText("پرس سینه دمبل");
  await expect(page.getByRole("heading", { name: "روش اجرای حرکت" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "نکات فرم و ایمنی" })).toBeVisible();
  expect(await page.locator('nav[aria-label="مسیر صفحه"] a').count()).toBe(2);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  expect(errors).toEqual([]);
});
test("home preserves cinematic content and CTA reaches onboarding", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/");
  await expect(page.getByTestId("landing-film")).toBeVisible();
  await expect(page.locator("h1")).toBeVisible();
  await page.locator('.cinematic-hero a[href="/get-started"]').click();
  await expect(page).toHaveURL(/\/get-started$/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, follow");
  expect(errors).toEqual([]);
});
test("private member route still requires authentication", async ({ page }) => {
  await page.goto("/workout-plan");
  await expect(page).toHaveURL(/\/login/);
  await expect(page.locator('meta[name="robots"]')).toHaveAttribute("content", "noindex, follow");
});
test("service worker cannot replace public or unknown navigation with member HTML", async ({ page, request }) => {
  await page.goto("/");
  await page.evaluate(async () => { await navigator.serviceWorker.ready; });
  await page.reload();
  await page.goto("/tools/protein-calculator");
  await page.getByRole("button", { name: "محاسبه نتیجه", exact: true }).click();
  await expect(page.locator("output")).toContainText("98 – 140");
  const response = await page.goto("/unknown-after-sw");
  expect(response?.status()).toBe(404);
  await expect(page.getByRole("heading", { name: "صفحه پیدا نشد" })).toBeVisible();
  expect((await request.get("/api/v1/auth/me")).status()).toBe(401);
});


test("reading pages keep Persian RTL and fit every tested viewport", async ({ page }) => {
  for (const record of pages.filter(record => record.sections.length > 0)) {
    await page.goto(record.path);
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("dir", "rtl");
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), record.path).toBe(true);
  }
});


test("cached cinematic home works when its origin is actually unavailable", async ({ page, baseURL }) => {
  // Stop an isolated forwarding origin instead of Playwright's broken WebKit offline emulation.
  // Upstream: https://github.com/microsoft/playwright/issues/42775
  const origin = createServer(async (request, response) => {
    try {
      const upstream = await fetch(`${baseURL}${request.url}`);
      response.statusCode = upstream.status;
      for (const [name, value] of upstream.headers) {
        if (!["content-encoding", "content-length", "transfer-encoding", "connection"].includes(name)) response.setHeader(name, value);
      }
      response.end(Buffer.from(await upstream.arrayBuffer()));
    } catch { response.writeHead(502).end(); }
  });
  await new Promise<void>(resolve => origin.listen(0, "127.0.0.1", resolve));
  try {
    await page.goto(`http://127.0.0.1:${(origin.address() as AddressInfo).port}/`);
    await page.evaluate(async () => { await navigator.serviceWorker.ready; });
    await page.reload();
    await expect.poll(() => page.evaluate(() => Boolean(navigator.serviceWorker.controller))).toBe(true);
    origin.closeAllConnections();
    await new Promise<void>((resolve, reject) => origin.close(error => error ? reject(error) : resolve()));
    await page.reload({ waitUntil: "domcontentloaded" });
    await expect(page.locator("h1")).toBeVisible();
    await expect(page.getByTestId("landing-film")).toBeVisible();
  } finally {
    if (origin.listening) { origin.closeAllConnections(); await new Promise<void>(resolve => origin.close(() => resolve())); }
  }
});


test("tool hub exposes exactly three crawlable calculator cards", async ({ page }) => {
  await page.goto("/tools");
  await expect(page.locator(".tool-card")).toHaveCount(3);
  for (const kind of ["calorie", "protein", "bmi"]) {
    await expect(page.locator(`.tool-card[href="/tools/${kind}-calculator"]`)).toBeVisible();
  }
});

test("calculator layouts and results work from small phones to desktop", async ({ page }, testInfo) => {
  test.setTimeout(90000);
  for (const width of [360, 390, 430, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const kind of ["calorie", "protein", "bmi"]) {
      await page.goto(`/tools/${kind}-calculator`);
      await expect(page.locator(".public-knowledge")).toHaveAttribute("dir", "rtl");
      await page.getByLabel("وزن", { exact: true }).fill("250");
      await page.getByRole("button", { name: "محاسبه نتیجه", exact: true }).click();
      await expect(page.locator("output")).toContainText(kind === "calorie" ? "4,139" : kind === "protein" ? "350 – 500" : "81.6");
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
      const controls = await page.locator(".tool-field input, .tool-field select, .tool-submit, .tool-switcher a").evaluateAll(elements => elements.map(element => element.getBoundingClientRect().height));
      expect(controls.every(height => height >= 44)).toBe(true);
      await page.getByLabel("وزن", { exact: true }).focus();
      await expect(page.getByLabel("وزن", { exact: true })).toBeFocused();
      expect(await page.getByLabel("وزن", { exact: true }).evaluate(element => getComputedStyle(element).outlineStyle)).not.toBe("none");
      if (testInfo.project.name === "desktop") await page.locator(".fitician-tool").screenshot({ path: testInfo.outputPath(`${kind}-${width}.png`) });
    }
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await page.locator(".tool-field input").first().evaluate(element => getComputedStyle(element).transitionDuration)).toBe("0s");
});

test("BMI remains readable without JavaScript and cannot transmit form values", async ({ browser, baseURL }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  try {
    const page = await context.newPage();
    await page.goto(`${baseURL}/tools/bmi-calculator`);
    await expect(page.getByRole("heading", { level: 1 })).toContainText("BMI");
    await expect(page.getByRole("heading", { name: "توده بدنی با ترکیب بدن یکسان نیست" })).toBeVisible();
    await expect(page.getByRole("button", { name: "محاسبه نتیجه", exact: true })).toBeDisabled();
    const requests: string[] = [];
    page.on("request", request => requests.push(request.url()));
    await page.getByLabel("وزن", { exact: true }).fill("80");
    await page.getByLabel("وزن", { exact: true }).press("Enter");
    await expect(page).toHaveURL(`${baseURL}/tools/bmi-calculator`);
    expect(requests).toEqual([]);
  } finally { await context.close(); }
});


test("API and media paths retain proxy precedence over static extension rules", async ({ request }) => {
  const api = await request.get("/api/seo-fixture.json");
  expect(api.status()).toBe(200);
  expect(await api.json()).toEqual({ source: "backend" });
  const media = await request.get("/media/seo-fixture.gif");
  expect(media.status()).toBe(200);
  expect(await media.text()).toBe("backend-media");
});


test("saved English home preference uses the client shell without hydration errors", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error" && /hydration|hydrating|Minified React error #(?:418|423|425)/i.test(message.text())) errors.push(message.text());
  });
  await page.addInitScript(() => localStorage.setItem("fitician-language", "en"));
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await expect(page.locator("html")).toHaveAttribute("dir", "ltr");
  await expect(page.locator("h1")).toHaveText("Every body needs its own plan.");
  expect(errors).toEqual([]);
});


test("saved member Light preference keeps public calculator headers readable", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("fitician.theme", "light"));
  for (const kind of ["calorie", "protein", "bmi"]) {
    await page.goto(`/tools/${kind}-calculator`);
    for (const selector of [".tool-intro", ".tool-eyebrow"]) {
      const contrast = await page.locator(selector).evaluate(element => {
        function luminance(color: string) {
          const channels = color.match(/[\d.]+/g)!.slice(0, 3).map(Number).map(value => {
            const channel = value / 255;
            return channel <= .04045 ? channel / 12.92 : ((channel + .055) / 1.055) ** 2.4;
          });
          return channels[0] * .2126 + channels[1] * .7152 + channels[2] * .0722;
        }
        const foreground = luminance(getComputedStyle(element).color);
        const background = luminance(getComputedStyle(element.closest(".public-knowledge")!).backgroundColor);
        return (Math.max(foreground, background) + .05) / (Math.min(foreground, background) + .05);
      });
      expect(contrast, `${kind} ${selector}`).toBeGreaterThanOrEqual(4.5);
    }
    expect(await page.evaluate(() => localStorage.getItem("fitician.theme"))).toBe("light");
    await expect(page.locator("html")).toHaveAttribute("data-fitician-theme", "light");
  }
});
