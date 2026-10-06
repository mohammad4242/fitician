import "../i18n";
import { useEffect } from "react";
import { BrowserRouter, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "../features/auth/AuthContext";
import { PublicLandingPage } from "../features/landing/PublicLandingPage";
import { SeoHead } from "./SeoHead";
import { resolveSeo } from "./registry";
import { PwaUpdatePrompt } from "../pwa/PwaUpdatePrompt";
export function HomeContent() {
  const { user } = useAuth();
  const location = useLocation();
  useEffect(() => {
    if (location.pathname !== "/") window.location.assign(location.pathname + location.search + location.hash);
  }, [location.pathname, location.search, location.hash]);
  return user ? <Navigate to="/dashboard" replace /> : <><SeoHead seo={resolveSeo("/")} /><PublicLandingPage /></>;
}
export function HomeApp() {
  return <BrowserRouter><AuthProvider><HomeContent /><PwaUpdatePrompt /></AuthProvider></BrowserRouter>;
}
