import { expect, test } from "@playwright/test";
import { publicExerciseFixture } from "./public-fixture";
import exercises from "../src/seo/exercise-data.json" with { type: "json" };

test.beforeEach(async ({ page }) => { await publicExerciseFixture(page); });

test("anonymous member-quality browsing preserves filters across detail and back", async ({ page }) => {
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  await page.goto("/exercise-library");
  await page.getByRole("button", { name: "صفحه بعد", exact: true }).click();
  await expect(page).toHaveURL(/page=2/);
  await page.getByRole("button", { name: /بالاتنه.*Upper Body/ }).click();
  await page.getByRole("button", { name: /سینه.*Chest/ }).click();
  await page.getByRole("button", { name: /میان‌سینه.*Mid Chest/ }).click();
  await page.getByRole("combobox", { name: "تجهیزات", exact: true }).selectOption("dumbbell");
  await page.getByRole("combobox", { name: "سطح سختی", exact: true }).selectOption("intermediate");
  await page.getByRole("searchbox").fill("Dumbbell Bench");
  const card = page.getByRole("article", { name: "پرس سینه دمبل", exact: true });
  await expect(card).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://fitician.fit/exercise-library");
  await card.getByRole("link", { name: "مشاهده حرکت", exact: true }).click();
  await expect(page.locator("h1")).toHaveText("پرس سینه دمبل");
  await expect(page.getByTestId("exercise-media-carousel")).toBeVisible();
  await expect(page.getByRole("heading", { name: "روش اجرای صحیح" })).toBeVisible();
  await expect(page.locator('link[rel="canonical"]')).toHaveAttribute("href", "https://fitician.fit/exercise-library/dumbbell-bench-press");
  await expect(page.locator('a[href^="/admin"], button[data-testid="delete-exercise"]')).toHaveCount(0);
  await page.locator(".exercise-detail-back").click();
  await expect(page.getByRole("searchbox")).toHaveValue("Dumbbell Bench");
  await expect(page.getByRole("combobox", { name: "تجهیزات", exact: true })).toHaveValue("dumbbell");
  await page.getByRole("searchbox").fill("missing exercise");
  await expect(card).toHaveCount(0);
  expect(errors).toEqual([]);
});

test("all approved exercises contain useful HTML before hydration", async ({ request }) => {
  for (const exercise of exercises) {
    const html = await (await request.get(`/exercise-library/${exercise.slug}`)).text();
    for (const text of [exercise.name_fa, exercise.name_en, ...exercise.instructions_fa, ...exercise.safety_notes_fa]) expect(html).toContain(text);
    expect(html).toContain("exercise-detail-sheet");
    expect(html).not.toMatch(/source_id|is_programmable|needs_review|substitution_group/);
  }
  const html = await (await request.get("/exercise-library?search=bench&equipment=dumbbell&page=2")).text();
  expect(html).toContain('href="https://fitician.fit/exercise-library"');
  const sitemap = await (await request.get("/sitemap-1.xml")).text();
  expect(sitemap).not.toContain("?search=");
});

test("premium discovery, dedicated pages and public shell fit five widths", async ({ page }, testInfo) => {
  test.setTimeout(120000);
  const errors: string[] = [];
  page.on("pageerror", error => errors.push(error.message));
  for (const width of [360, 390, 430, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    for (const path of ["/workout-program", "/nutrition", "/body-analysis", "/learn", "/about", "/exercise-library", "/exercise-library/dumbbell-bench-press"]) {
      await page.goto(path);
      await expect(page.locator("h1")).toBeVisible();
      await expect(page.locator("footer")).toHaveCount(1);
      await expect(page.locator(".fitician-brand-logo").first()).toBeVisible();
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `${path} ${width}`).toBe(true);
      if (width === 390 && testInfo.project.name === "desktop") await page.screenshot({ path: testInfo.outputPath(`${path.replaceAll("/", "-")}.png`), fullPage: true });
    }
    await page.goto("/");
    await expect(page.locator(".discovery-card")).toHaveCount(6);
    await page.locator(".public-discovery").scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await expect(page.locator("footer")).toHaveCount(1);
  }
  await page.emulateMedia({ reducedMotion: "reduce" });
  expect(await page.locator(".discovery-card").first().evaluate(element => parseFloat(getComputedStyle(element).transitionDuration))).toBeLessThanOrEqual(.00001);
  expect(errors).toEqual([]);
});
