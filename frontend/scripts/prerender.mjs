import { readFile, writeFile, mkdir, readdir, rm } from "node:fs/promises";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { generateSW } from "workbox-build";
import { publicPaths, render, sitemapDocuments, robotsText, memberRouteSources, publicPayload } from "../dist-server/render.js";
// Remove historical audit exports from generated output; never publish internal reports.
for (const entry of await readdir("dist")) {
  if (/^(?:fitician|fitsho)_.*report.*\.html$|^workout_engine_.*\.html$/.test(entry)) await rm(join("dist", entry));
}
const template = await readFile("dist/index.html", "utf8");
const headless = template.replace(/<title>[\s\S]*?<\/title>/g, "").replace(/<meta\s+name="description"[\s\S]*?\/>/g, "");
const app = headless.replace("</head>", '<title data-fitician-seo="true">فیتیشن | Fitician</title><meta data-fitician-seo="true" name="robots" content="noindex, follow" /></head>');
await writeFile("dist/app.html", app);
const manifest = JSON.parse(await readFile("dist/.vite/manifest.json", "utf8"));
function documentFor(path) {
  const html = render(path);
  const modulePath = path === "/" ? "src/seo/HomeApp.tsx" : ["/privacy", "/support", "/install"].includes(path) ? "src/App.tsx" : path.startsWith("/exercise-library") ? "src/seo/PublicExerciseApp.tsx" : "src/seo/PublicApp.tsx";
  const styles = new Set();
  function collectCss(key) {
    const entry = manifest[key];
    if (!entry) return;
    for (const css of entry.css ?? []) styles.add(css);
    for (const child of entry.imports ?? []) collectCss(child);
  }
  collectCss(modulePath);
  const headTags = [...styles].filter(css => !headless.includes(`href="/${css}"`)).map(css => `<link rel="stylesheet" href="/${css}" />`);
  const body = html.replace(/<title[^>]*>[\s\S]*?<\/title>|<meta\s[^>]*\/>|<link\s[^>]*\/>/g, tag => { headTags.push(tag); return ""; });
  const knowledge = path !== "/" && !["/privacy", "/support", "/install", "/404"].includes(path);
  const payload = knowledge ? `<script id="public-page-data" type="application/json">${JSON.stringify(publicPayload(path)).replaceAll("<", "\\u003c")}</script>` : "";
  return headless.replace("</head>", `${headTags.join("")}\n</head>`).replace('<div id="root"></div>', `<div id="root" data-prerendered="true"${knowledge ? ' data-public-kind="knowledge"' : ""}>${body}</div>${payload}`);
}
for (const path of publicPaths()) {
  const directory = path === "/" ? "dist" : join("dist", path.slice(1));
  await mkdir(directory, { recursive: true });
  await writeFile(join(directory, "index.html"), documentFor(path));
}
await writeFile("dist/404.html", documentFor("/404"));
await writeFile("dist/robots.txt", robotsText());
for (const [name, xml] of Object.entries(sitemapDocuments())) await writeFile(join("dist", name), xml);
await writeFile("dist/nginx-member-routes.conf", `location ~ ^/(?:${memberRouteSources.join("|")})/?$ {\n    add_header X-Robots-Tag "noindex, follow" always;\n    add_header Cache-Control "no-cache" always;\n    try_files /app.html =404;\n}\n`);
// Generate AFTER rendering so revision hashes cover the delivered HTML.
const sw = await generateSW({
  globDirectory: "dist", swDest: "dist/sw.js", cleanupOutdatedCaches: true,
  globPatterns: ["**/*.{js,css,woff,woff2}", "index.html", "app.html"],
  globIgnores: ["sw.js", "workbox-*.js", "**/mediapipe/**", "**/heic-*.js", "**/exercises/**", "**/api/**", "**/media/**"],
  additionalManifestEntries: ["/pwa/icon-192.png", "/pwa/icon-512.png", "/pwa/icon-maskable-512.png", "/pwa/apple-touch-icon.png"].map(url => ({ url, revision: null })),
  navigateFallback: "/app.html",
  navigateFallbackAllowlist: [new RegExp(`^/(?:${memberRouteSources.join("|")})/?(?:\\?.*)?$`)],
});
if (sw.warnings.length) throw new Error(sw.warnings.join("\n"));
const homeHash = createHash("sha256").update(await readFile("dist/index.html")).digest("hex");
console.log(`Prerendered ${publicPaths().length} canonical public pages; home sha256 ${homeHash}; service worker ${sw.count} resources`);
