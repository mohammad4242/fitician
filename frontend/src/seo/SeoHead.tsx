import type { Seo } from "./registry";
export function SeoHead({ seo }: { seo: Seo }) {
  return <>
    <title data-fitician-seo="true">{seo.title}</title>
    <meta data-fitician-seo="true" name="description" content={seo.description} />
    <meta data-fitician-seo="true" name="robots" content={seo.robots} />
    <link data-fitician-seo="true" rel="canonical" href={seo.canonical} />
    <meta data-fitician-seo="true" property="og:type" content="website" />
    <meta data-fitician-seo="true" property="og:title" content={seo.ogTitle} />
    <meta data-fitician-seo="true" property="og:description" content={seo.ogDescription} />
    <meta data-fitician-seo="true" property="og:image" content={seo.ogImage} />
    <meta data-fitician-seo="true" property="og:url" content={seo.ogUrl} />
    <meta data-fitician-seo="true" property="og:site_name" content="Fitician" />
    <meta data-fitician-seo="true" property="og:locale" content="fa_IR" />
    <meta data-fitician-seo="true" name="twitter:card" content={seo.twitterCard} />
    <meta data-fitician-seo="true" name="twitter:title" content={seo.ogTitle} />
    <meta data-fitician-seo="true" name="twitter:description" content={seo.ogDescription} />
    <meta data-fitician-seo="true" name="twitter:image" content={seo.ogImage} />
    {seo.alternates.map(alternate => <link data-fitician-seo="true" key={alternate.language} rel="alternate" hrefLang={alternate.language} href={alternate.url} />)}
    {seo.jsonLd.length > 0 && <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(seo.jsonLd).replaceAll("<", "\\u003c").replaceAll(">", "\\u003e").replaceAll("&", "\\u0026") }} />}
  </>;
}
