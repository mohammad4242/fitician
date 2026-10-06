import type { Page } from "@playwright/test";
import exercises from "../src/seo/exercise-data.json" with { type: "json" };
import categories from "../src/seo/exercise-categories.json" with { type: "json" };

// The nginx fixture has no database. Only explicit public projections are served here.
export async function publicExerciseFixture(page: Page) {
  await page.route("**/api/v1/public/**", async route => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("exercise-categories")) return route.fulfill({ json: categories });
    const slug = url.pathname.split("/exercises/")[1];
    if (slug) {
      const exercise = exercises.find(item => item.slug === slug);
      return route.fulfill(exercise ? { json: exercise } : { status: 404, json: { detail: "Not found" } });
    }
    const query = url.searchParams;
    const filtered = exercises.filter(item => {
      for (const key of ["body_region", "primary_muscle", "muscle_focus", "difficulty", "content_type"] as const) {
        if (query.has(key) && item[key] !== query.get(key)) return false;
      }
      if (query.has("equipment") && !item.equipment.includes(query.get("equipment")!)) return false;
      const search = query.get("search")?.toLowerCase();
      return !search || `${item.name_fa} ${item.name_en}`.toLowerCase().includes(search);
    });
    const pageNumber = Number(query.get("page") ?? 1), size = Number(query.get("page_size") ?? 12);
    await route.fulfill({ json: { items: filtered.slice((pageNumber - 1) * size, pageNumber * size), total: filtered.length, page: pageNumber, page_size: size, total_pages: Math.max(1, Math.ceil(filtered.length / size)) } });
  });
  await page.route("**/media/exercises/**", route => route.fulfill({ contentType: "image/gif", body: Buffer.from("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", "base64") }));
}
