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
  await page.getByRole("button", { name: "محاسبه", exact: true }).click();
  await expect(page.locator("output")).toContainText("1979");
  await expect(page).toHaveTitle(resolveSeo("/tools/calorie-calculator").title);
  expect(await page.locator('meta[name="description"]').count()).toBe(1);
  expect(await page.locator('link[rel="canonical"]').count()).toBe(1);
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("link", { name: "محاسبه پروتئین روزانه برای افراد فعال", exact: true }).click();
  await page.getByRole("button", { name: "محاسبه", exact: true }).click();
  await expect(page.locator("output")).toContainText("98 تا 140");
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
  await page.getByRole("button", { name: "محاسبه", exact: true }).click();
  await expect(page.locator("output")).toContainText("98 تا 140");
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
