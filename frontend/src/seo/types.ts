export type Seo = {
  title: string; description: string; canonical: string; robots: "index, follow" | "noindex, follow";
  ogTitle: string; ogDescription: string; ogImage: string; ogUrl: string;
  twitterCard: "summary" | "summary_large_image"; language: "fa" | "en";
  alternates: { language: string; url: string }[]; jsonLd: Record<string, unknown>[];
};
// A page can override metadata without weakening the default private-route policy.
export type SeoOverrides = Partial<Seo>;
