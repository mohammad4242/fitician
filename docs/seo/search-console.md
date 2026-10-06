# After deployment

1. Confirm the intended production origin is `https://fitician.fit`; Caddy owns HTTPS and www-to-apex redirects. For another origin, update the central registry and repository support branding consistently before building. Never deploy a staging build as indexable production content.
2. In Search Console, add a Domain property for fitician.fit. Copy Google's actual DNS TXT record to the DNS provider and verify. No fake HTML verification token is included.
3. Request `/robots.txt`, `/sitemap.xml` and `/sitemap-1.xml` from production. Confirm 200, correct origin and public URLs only. Submit `https://fitician.fit/sitemap.xml` in Sitemaps.
4. Inspect `/`, `/workout-program`, `/nutrition`, `/tools/calorie-calculator`, `/tools/protein-calculator`, `/tools/bmi-calculator` and `/exercise-library/dumbbell-bench-press` using URL Inspection live tests. Check rendered HTML, canonical and indexability. Request indexing for key pages; indexing/rankings are not guaranteed.
5. Inspect an unknown public URL (404) and login/member shell (noindex). Check crawler access to JS/CSS/fonts. robots.txt permits crawlers seeing member noindex; authentication remains the data boundary.
6. Run Rich Results Test on home, article and exercise examples. Organization/WebSite/BreadcrumbList/Article are used where truthful; generic WebPage markup does not imply a special rich result. No FAQ, rating or offer claims.
7. Monitor Page Indexing, sitemap processing, Crawl Stats, security/manual actions and Core Web Vitals. Review soft-404, duplicate canonical and excluded-URL trends after releases.
8. In Performance, compare Persian queries and landing pages by impressions, clicks, CTR and position over 28-day windows. Avoid judging a new page from a few days of data. Use outcomes to improve existing pages before adding clusters.
9. Measure real-user CWV at the 75th percentile, separating home from reading/tool templates. Good thresholds: LCP ≤2.5s, INP ≤200ms, CLS ≤0.1. Local browser checks cannot establish these field metrics.

Deployment was not performed by this implementation. Search Console ownership, production indexing, CDN media availability and field CWV require owner-side verification after release.
