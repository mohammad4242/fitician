import { renderToStaticMarkup } from "react-dom/server";
import { expect, it } from "vitest";
import { PublicPage } from "./PublicPage";
import { PublicExercisePage } from "./PublicExercises";
import { publicExercises, publicPaths, sitemapDocuments, publicPayload } from "./registry";
import { memberNavigationPattern } from "./routePolicy";
it("renders public headings, references, links and RTL before JavaScript", () => {
  for (const path of publicPaths().filter(path => !["/", "/privacy", "/support", "/install"].includes(path))) {
    const Component = path.startsWith("/exercise-library") ? PublicExercisePage : PublicPage;
    const html = renderToStaticMarkup(<Component payload={publicPayload(path)} />);
    expect(html).toContain('dir="rtl"');
    expect(html).toMatch(/<h1[ >]/);
    expect(html).toContain('href="/get-started"');
    expect(html).not.toContain("<video");
  }
});
it("exports only instructional exercise fields with unique slugs", () => {
  expect(publicExercises.length).toBeGreaterThan(0);
  expect(new Set(publicExercises.map(exercise => exercise.slug)).size).toBe(publicExercises.length);
  for (const exercise of publicExercises) {
    expect(exercise.instructions_fa.length).toBeGreaterThanOrEqual(3);
    expect(exercise.safety_notes_fa.length).toBeGreaterThan(0);
    for (const field of ["id", "source_id", "caution_tags", "is_programmable", "needs_review", "substitution_group"]) expect(exercise).not.toHaveProperty(field);
  }
});
it("shards canonical public sitemap URLs without fake timestamps", () => {
  const xml = sitemapDocuments(publicPaths(), 2);
  expect(Object.keys(xml).length).toBe(Math.ceil(publicPaths().length / 2) + 1);
  expect(Object.values(xml).join("")).not.toContain("lastmod");
});
it("limits PWA fallback to legitimate member routes", () => {
  for (const path of ["/dashboard", "/exercises/dumbbell-bench-press", "/body-progress/123", "/admin/support", "/get-started"]) expect(memberNavigationPattern.test(path)).toBe(true);
  for (const path of ["/workout-program", "/exercise-library/missing", "/api/v1/exercises", "/media/missing", "/assets/missing.js", "/invalid", "/dashboard/invalid"]) expect(memberNavigationPattern.test(path)).toBe(false);
});
