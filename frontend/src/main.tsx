import "@fontsource/lalezar";
import "@fontsource-variable/sora";
import "@fontsource-variable/vazirmatn";
import { StrictMode } from "react";
import { createRoot, hydrateRoot } from "react-dom/client";

import type { PublicPayload } from "./seo/registry";
import "./seo/public.css";
import "./index.css";
import "./pwa/pwa.css";
import { applyDesignSystem } from "./styles/designSystem";
import { readTheme } from "./theme/ThemeProvider";

applyDesignSystem(document.documentElement, readTheme());

const path = window.location.pathname;
const root = document.getElementById("root")!;
const legacyPublic = ["/privacy", "/support", "/install"];
async function start() {
  let element;
  if (path === "/") {
    if (document.documentElement.lang !== "fa") root.removeAttribute("data-prerendered");
    const { HomeApp } = await import("./seo/HomeApp");
    element = <HomeApp />;
  } else if (root.dataset.publicKind === "knowledge" || (import.meta.env.DEV && !legacyPublic.includes(path) && (await import("./seo/registry")).findPublicPage(path))) {
    document.documentElement.lang = "fa";
    document.documentElement.dir = "rtl";
    const { PublicApp } = await import("./seo/PublicApp");
    const data = document.getElementById("public-page-data")?.textContent;
    const payload: PublicPayload = data ? JSON.parse(data) : (await import("./seo/registry")).publicPayload(path);
    element = <PublicApp payload={payload} />;
  } else {
    const { default: App } = await import("./App");
    // Existing public components have their own auth/PWA providers and client state.
    root.removeAttribute("data-prerendered");
    element = <App />;
  }
  if (root.dataset.prerendered === "true") hydrateRoot(root, <StrictMode>{element}</StrictMode>);
  else {
    // Hand ownership of build-rendered metadata to React when using the legacy CSR shell.
    document.head.querySelectorAll("[data-fitician-seo]").forEach(node => node.remove());
    createRoot(root).render(<StrictMode>{element}</StrictMode>);
  }
}
void start();
