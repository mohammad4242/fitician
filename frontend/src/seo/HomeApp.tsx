import "../i18n";
import { useEffect } from "react";
import { BrowserRouter, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "../features/auth/AuthContext";
import { PublicLandingPage } from "../features/landing/PublicLandingPage";
import { SeoHead } from "./SeoHead";
import type { Seo } from "./types";
import { PwaUpdatePrompt } from "../pwa/PwaUpdatePrompt";
export function HomeContent({ seo }: { seo: Seo }) {
  const { user } = useAuth();
  const location = useLocation();
  useEffect(() => {
    if (location.pathname !== "/") window.location.assign(location.pathname + location.search + location.hash);
  }, [location.pathname, location.search, location.hash]);
  return user ? <Navigate to="/dashboard" replace /> : <><SeoHead seo={seo} /><PublicLandingPage /></>;
}
export function HomeApp({ seo }: { seo: Seo }) {
  return <BrowserRouter><AuthProvider><HomeContent seo={seo} /><PwaUpdatePrompt /></AuthProvider></BrowserRouter>;
}
