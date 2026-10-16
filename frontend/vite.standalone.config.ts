import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  root: resolve(import.meta.dirname, "standalone"),
  publicDir: false,
  plugins: [
    react(),
    {
      name: "standalone-install-assets",
      generateBundle() {
        for (const asset of ["apple-touch-icon.png", "icon-192.png"]) {
          this.emitFile({
            type: "asset",
            fileName: `pwa/${asset}`,
            source: readFileSync(resolve(import.meta.dirname, "public/pwa", asset)),
          });
        }
      },
    },
  ],
  build: {
    outDir: resolve(import.meta.dirname, "dist-standalone"),
    emptyOutDir: true,
    rollupOptions: {
      input: resolve(import.meta.dirname, "standalone/index.html"),
    },
  },
});
