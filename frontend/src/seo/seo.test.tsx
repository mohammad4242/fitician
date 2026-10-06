import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { pages, resolveSeo, publicPaths, sitemapDocuments, robotsText } from "./registry";
import { SeoHead } from "./SeoHead";
import { calculateCalories, calculateProtein } from "./calculators";

describe("public SEO contract", () => {
  it("gives every public page unique canonical metadata and accurate schema", () => {
    expect(new Set(pages.map(p => p.title)).size).toBe(pages.length);
    for (const path of publicPaths()) {
      const seo = resolveSeo(path);
      expect(seo.robots).toBe("index, follow");
      expect(seo.canonical).toBe(`https://fitician.fit${path === "/" ? "/" : path}`);
      const html = renderToStaticMarkup(<SeoHead seo={seo} />);
      expect(html).toContain('name="description"');
      expect(html).toContain('property="og:url"');
      expect(html).toContain('name="twitter:card"');
      expect(html).toContain('application/ld+json');
      expect(html).not.toContain('FAQPage');
      expect(html).not.toContain('aggregateRating');
    }
  });
  it("excludes private, onboarding, auth and invalid routes", () => {
    const paths = ["/login", "/register", "/get-started", "/reset-password", "/dashboard", "/profile", "/plans", "/billing/history", "/admin/support", "/support/tickets", "/workout-plan", "/nutrition-estimate", "/body-progress", "/exercises", "/missing"];
    const documents = sitemapDocuments();
    const xml = Object.values(documents).join("");
    for (const path of paths) {
      expect(resolveSeo(path).robots).toBe("noindex, follow");
      expect(xml).not.toContain(`<loc>https://fitician.fit${path}</loc>`);
    }
    for (const path of publicPaths()) expect(xml).toContain(`<loc>https://fitician.fit${path}</loc>`);
    expect(robotsText()).toContain("Sitemap: https://fitician.fit/sitemap.xml");
    expect(robotsText()).not.toContain("Disallow: /login");
  });
  it("escapes JSON-LD script injection", () => {
    const seo = { ...resolveSeo("/"), jsonLd: [{ name: "</script><script>alert(1)</script>" }] };
    const html = renderToStaticMarkup(<SeoHead seo={seo} />);
    expect(html).not.toContain("</script><script>");
    expect(html).toContain("\\u003c");
  });
});
describe("scientifically bounded public calculators", () => {
  it("uses Mifflin St Jeor with explicit activity factors", () => {
    expect(calculateCalories({ age: 30, sex: "male", weight: 70, height: 175, activity: 1.2 })).toEqual({ resting: 1649, maintenance: 1979 });
    expect(calculateCalories({ age: 30, sex: "female", weight: 70, height: 175, activity: 1.2 })).toEqual({ resting: 1483, maintenance: 1779 });
  });
  it("rejects non-finite, unsupported and out-of-scope values", () => {
    for (const weight of [0, -1, NaN, Infinity, 500]) expect(() => calculateProtein(weight)).toThrow();
    expect(() => calculateCalories({ age: 17, sex: "male", weight: 70, height: 175, activity: 1.2 })).toThrow();
    expect(() => calculateCalories({ age: 30, sex: "male", weight: 70, height: 175, activity: 99 })).toThrow();
  });
  it("returns a range rather than a prescription", () => expect(calculateProtein(70)).toEqual({ low: 98, high: 140 }));
});

it("keeps dynamic route metadata after member navigation", () => {
  expect(resolveSeo("/workout-plan").robots).toBe("noindex, follow");
  expect(resolveSeo("/support").robots).toBe("index, follow");
  expect(resolveSeo("/support/tickets/example").robots).toBe("noindex, follow");
});

it("keeps structured data consistent with visible article content", () => {
  for (const page of pages.filter(page => page.article)) {
    const schemas = resolveSeo(page.path).jsonLd;
    const article = schemas.find(schema => schema["@type"] === "Article");
    expect(article?.headline).toBe(page.title);
    expect(article?.datePublished).toBe(page.published);
    expect(article).not.toHaveProperty("reviewedBy");
    expect(article).not.toHaveProperty("dateModified");
    expect(article?.citation).toEqual(page.references?.map(ref => ref.url));
  }
});
