import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { memberNavigationPattern } from "./src/seo/routePolicy.ts";
import react from "@vitejs/plugin-react";
import { VitePWA, type ManifestOptions } from "vite-plugin-pwa";
import { defineConfig } from "vitest/config";

export function resolveApiProxyTarget(value: string | undefined): string {
  return value?.trim() || "http://localhost:8001";
}

const apiProxyTarget = resolveApiProxyTarget(process.env.VITE_API_PROXY_TARGET);
const apiProxy = {
  "/api": {
    target: apiProxyTarget,
    changeOrigin: false,
  },
  "^/media(?:/|$)": {
    target: apiProxyTarget,
    changeOrigin: false,
  },
};

export const pwaManifest = {
  name: "Fitician | فیتیشن",
  short_name: "Fitician",
  description: "فیتیشن؛ همراه هوشمند تمرین، تغذیه و تحلیل بدن.",
  lang: "fa",
  dir: "rtl",
  id: "/",
  start_url: "/",
  scope: "/",
  display: "standalone",
  background_color: "#020607",
  theme_color: "#020607",
  icons: [
    { src: "/pwa/icon-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
    { src: "/pwa/icon-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
    { src: "/pwa/icon-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
  ],
} satisfies Partial<ManifestOptions>;

export function previewDocumentPath(path: string) {
  if (path === "/") return "index.html";
  if (memberNavigationPattern.test(path)) return "app.html";
  if (/^\/(?:api|media)(?:\/|$)/.test(path) || !/^\/[a-z0-9-]+(?:\/[a-z0-9-]+)*$/.test(path)) return undefined;
  return `${path.slice(1)}/index.html`;
}

export default defineConfig({
  plugins: [
    {
      name: "prerender-preview",
      configurePreviewServer(server) {
        server.middlewares.use((request, response, next) => {
          const file = previewDocumentPath(new URL(request.url ?? "/", "http://localhost").pathname);
          if (!file || !["GET", "HEAD"].includes(request.method ?? "")) return next();
          const document = join(server.config.root, server.config.build.outDir, file);
          if (!existsSync(document)) return next();
          response.setHeader("Content-Type", "text/html; charset=utf-8");
          response.end(request.method === "HEAD" ? undefined : readFileSync(document));
        });
      },
    },
    react(),
    VitePWA({
      disable: process.env.SEO_SERVER === "1",
      registerType: "prompt",
      manifest: pwaManifest,
      workbox: {
        cleanupOutdatedCaches: true,
        globPatterns: ["**/*.{js,css,html,woff,woff2}"],
        globIgnores: [
          "**/fitician_*_report*.html",
          "**/fitsho_*_report*.html",
          "**/workout_engine_*.html",
          "**/exercises/**",
          "**/image&videos/**",
          "**/mediapipe/**",
          "**/heic-*.js",
          "**/api/**",
          "**/media/**",
        ],
        additionalManifestEntries: [
          { url: "/pwa/icon-192.png", revision: null },
          { url: "/pwa/icon-512.png", revision: null },
          { url: "/pwa/icon-maskable-512.png", revision: null },
          { url: "/pwa/apple-touch-icon.png", revision: null },
        ],
        navigateFallback: "/app.html",
        navigateFallbackAllowlist: [memberNavigationPattern],
        navigateFallbackDenylist: [/^\/api(?:\/|$)/, /^\/media(?:\/|$)/],
      },
    }),
  ],
  build: { manifest: true },
  server: {
    host: "0.0.0.0",
    proxy: apiProxy,
  },
  preview: {
    proxy: apiProxy,
  },
  test: {
    environment: "jsdom",
    setupFiles: "./src/test/setup.ts",
    globals: true,
    exclude: ["**/node_modules/**", "e2e/**", "seo-e2e/**"],
  },
});
