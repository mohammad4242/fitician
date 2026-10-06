import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom";
import { AuthProvider } from "../features/auth/AuthContext";
import { PublicLandingPage } from "../features/landing/PublicLandingPage";
import { PrivacyPolicyPage } from "../features/accountDeletion/PrivacyPolicyPage";
import { HelpCenterPage } from "../features/support/SupportPages";
import { PublicInstallPage } from "../features/install/PublicInstallPage";
import { PublicPage, NotFound } from "./PublicPage";
import { SeoHead } from "./SeoHead";
import { publicPaths, resolveSeo, robotsText, sitemapDocuments, publicPayload } from "./registry";
import { memberRouteSources } from "./routePolicy";
import "../i18n";
export { publicPaths, resolveSeo, robotsText, sitemapDocuments, publicPayload, memberRouteSources };
export function render(path: string) {
  const content = path === "/" ? <PublicLandingPage /> : path === "/privacy" ? <PrivacyPolicyPage /> : path === "/support" ? <HelpCenterPage /> : path === "/install" ? <PublicInstallPage /> : path === "/404" ? <NotFound /> : <PublicPage payload={publicPayload(path)} />;
  return renderToString(<StaticRouter location={path}><AuthProvider><SeoHead seo={resolveSeo(path)} />{content}</AuthProvider></StaticRouter>);
}
