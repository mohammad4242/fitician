import categories from "./exercise-categories.json" with { type: "json" };
import type { ExerciseCategories } from "../features/exercises/types";
import type { ExercisePresentationDetail } from "../features/exercises/ExerciseDetailPresentation";
import type { CatalogExercise } from "../features/exercises/ExerciseCatalog";
import exercises from "./exercise-data.json" with { type: "json" };
import { contentPages, type PublicPage } from "./content";
export const siteOrigin = "https://fitician.fit";
import type { Seo } from "./types";
export type { Seo } from "./types";
export const publicExercises = exercises as ExercisePresentationDetail[];
export const publicCategories = categories as ExerciseCategories;
export const pages: PublicPage[] = [
  { path: "/", title: "فیتیشن؛ برنامه تمرین، تغذیه و تحلیل بدن", description: "فیتیشن؛ همراه هوشمند تمرین، تغذیه و تحلیل بدن برای برنامه‌ای متناسب با زندگی واقعی شما.", sections: [] },
  ...contentPages,
  { path: "/privacy", title: "سیاست حریم خصوصی فیتیشن", description: "اطلاعاتی که فیتیشن پردازش می‌کند، حفاظت از تصاویر خصوصی و کنترل‌های دسترسی و حذف حساب را بشناسید.", sections: [] },
  { path: "/support", title: "راهنما و پشتیبانی فیتیشن", description: "پاسخ به پرسش‌های استفاده از فیتیشن، راهنمای حساب و مسیر ارتباط با پشتیبانی.", sections: [] },
  { path: "/install", title: "نصب فیتیشن روی گوشی", description: "راهنمای نصب وب‌اپ فیتیشن روی اندروید و آیفون و دسترسی آسان به تمرین و تغذیه.", sections: [] },
  ...publicExercises.map(exercise => ({
    path: `/exercise-library/${exercise.slug}`, title: exercisePageTitle(exercise),
    description: `آموزش ${exercise.name_fa} (${exercise.name_en}): عضله هدف، تجهیزات، مراحل اجرا و نکات ایمنی از کتابخانه حرکات فیتیشن.`, sections: [], related: ["/exercise-library", "/workout-program", "/learn/beginner-training"],
  })),
];
const pageByPath = new Map(pages.map(page => [page.path, page]));
export function findPublicPage(path: string) { return pageByPath.get(path); }
export function publicPaths() { return pages.filter(page => page.seo?.robots !== "noindex, follow" && (!page.seo?.canonical || page.seo.canonical === canonicalUrl(page.path))).map(page => page.path); }
export function canonicalUrl(path: string) { return `${siteOrigin}${path}`; }
export function breadcrumbs(path: string) {
  const page = findPublicPage(path);
  const parent = path.startsWith("/exercise-library/") ? "/exercise-library" : path.startsWith("/learn/") ? "/learn" : path.startsWith("/tools/") ? "/tools" : undefined;
  return [ { path: "/", title: "فیتیشن" }, ...(parent ? [{ path: parent, title: findPublicPage(parent)!.title }] : []), ...(path !== "/" ? [{ path, title: page?.title ?? "صفحه پیدا نشد" }] : []) ];
}
export function resolveSeo(path: string): Seo {
  const page = findPublicPage(path);
  const canonical = canonicalUrl(page?.path ?? path.split("?")[0]);
  const title = page ? `${page.title} | Fitician` : "فیتیشن | Fitician";
  const description = page?.description ?? "ورود به تجربه شخصی فیتیشن؛ تمرین، تغذیه و پیگیری روند در حساب کاربری.";
  const jsonLd: Record<string, unknown>[] = page ? [
    { "@context": "https://schema.org", "@type": "WebPage", "@id": `${canonical}#page`, url: canonical, name: page.title, description, inLanguage: "fa", isPartOf: { "@id": `${siteOrigin}/#website` } },
  ] : [];
  if (path === "/") jsonLd.push(
    { "@context": "https://schema.org", "@type": "Organization", "@id": `${siteOrigin}/#organization`, name: "Fitician", alternateName: "فیتیشن", url: `${siteOrigin}/`, logo: `${siteOrigin}/pwa/icon-512.png` },
    { "@context": "https://schema.org", "@type": "WebSite", "@id": `${siteOrigin}/#website`, name: "Fitician", alternateName: "فیتیشن", url: `${siteOrigin}/`, inLanguage: "fa", publisher: { "@id": `${siteOrigin}/#organization` } },
  );
  if (page && path !== "/") jsonLd.push({ "@context": "https://schema.org", "@type": "BreadcrumbList", itemListElement: breadcrumbs(path).map((crumb, index) => ({ "@type": "ListItem", position: index + 1, name: crumb.title, item: canonicalUrl(crumb.path) })) });
  if (page?.article) jsonLd.push({ "@context": "https://schema.org", "@type": "Article", headline: page.title, description, mainEntityOfPage: canonical, inLanguage: "fa", datePublished: page.published, ...(page.updated ? { dateModified: page.updated } : {}), author: { "@type": "Organization", name: "Fitician", url: `${siteOrigin}/about` }, publisher: { "@type": "Organization", name: "Fitician", url: `${siteOrigin}/` }, citation: page.references?.map(ref => ref.url) });
  return { title, description, canonical, robots: page ? "index, follow" : "noindex, follow", ogTitle: title, ogDescription: description, ogImage: `${siteOrigin}/pwa/icon-512.png`, ogUrl: canonical, twitterCard: "summary_large_image", language: "fa", alternates: [], jsonLd, ...page?.seo };
}
function xmlEscape(value: string) { return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll('"', "&quot;"); }
export function sitemapDocuments(paths = publicPaths(), shardSize = 10000): Record<string, string> {
  if (!Number.isInteger(shardSize) || shardSize < 1 || shardSize > 50000) throw new RangeError("Invalid sitemap shard size");
  const output: Record<string, string> = {};
  const allowed = new Set(publicPaths());
  const canonicalPaths = [...new Set(paths)].filter(path => allowed.has(path));
  for (let offset = 0; offset < canonicalPaths.length; offset += shardSize) {
    const name = `sitemap-${offset / shardSize + 1}.xml`;
    output[name] = `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${canonicalPaths.slice(offset, offset + shardSize).map(path => `<url><loc>${xmlEscape(canonicalUrl(path))}</loc></url>`).join("")}</urlset>`;
  }
  output["sitemap.xml"] = `<?xml version="1.0" encoding="UTF-8"?><sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${Object.keys(output).map(name => `<sitemap><loc>${siteOrigin}/${name}</loc></sitemap>`).join("")}</sitemapindex>`;
  return output;
}
export function robotsText() { return `User-agent: *\nAllow: /\nDisallow: /api/\nDisallow: /media/private/\n\nSitemap: ${siteOrigin}/sitemap.xml\n`; }

export function publicPayload(path: string) {
  const page = findPublicPage(path);
  if (!page) throw new Error("Unknown public page");
  const exercise = publicExercises.find(record => path === `/exercise-library/${record.slug}`);
  const candidates = path === "/exercise-library" ? publicExercises : exercise ? relatedExercises(exercise) : [];
  return {
    page, seo: resolveSeo(path), crumbs: breadcrumbs(path), exercise,
    categories: path.startsWith("/exercise-library") ? publicCategories : undefined,
    exercises: candidates.map(catalogueSummary),
    articles: path === "/learn" ? pages.filter(record => record.article) : undefined,
    related: (page.related ?? []).map(link => ({ path: link, title: findPublicPage(link)!.title })),
    exerciseLinks: candidates.map(record => ({ path: `/exercise-library/${record.slug}`, title: record.name_fa, english: record.name_en })),
  };
}
export type PublicPayload = ReturnType<typeof publicPayload>;

function exercisePageTitle(exercise: ExercisePresentationDetail) {
  const sameName = publicExercises.filter(record => record.name_fa === exercise.name_fa);
  if (sameName.length === 1) return `${exercise.name_fa}؛ روش اجرا و ایمنی`;
  const ordinal = sameName.findIndex(record => record.slug === exercise.slug) + 1;
  return `${exercise.name_fa} (${exercise.name_en})؛ راهنمای اجرا ${ordinal}`;
}

function relatedExercises(exercise: ExercisePresentationDetail) {
  const muscle = publicExercises.filter(record => record.primary_muscle === exercise.primary_muscle && record.slug !== exercise.slug);
  return (muscle.length ? muscle : publicExercises.filter(record => record.body_region === exercise.body_region && record.slug !== exercise.slug)).slice(0, 4);
}

function catalogueSummary(exercise: ExercisePresentationDetail): CatalogExercise {
  const { slug, name_fa, name_en, content_type, body_region, primary_muscle,
    secondary_muscles, muscle_focus, equipment, difficulty, labels, media_path, media_type } = exercise;
  return { slug, name_fa, name_en, content_type, body_region, primary_muscle,
    secondary_muscles, muscle_focus, equipment, difficulty, labels, media_path, media_type };
}
