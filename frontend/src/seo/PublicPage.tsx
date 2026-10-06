import { PublicDiscovery } from "./PublicDiscovery";
import { Calculator } from "./Calculator";
import { ToolHeader, ToolHub } from "./Tools";
import { tools } from "./tools";
import type { PublicPayload } from "./registry";
import { PublicExercises } from "./PublicExercises";
import "./public.css";
export function PublicPage({ payload }: { payload: PublicPayload }) {
  const { page, crumbs, related } = payload;
  const path = page.path;
  const tool = tools.find(tool => tool.path === path);
  return <div className="public-knowledge" lang="fa" dir="rtl">
    <header><a className="public-brand" href="/">Fitician <span>فیتیشن</span></a><a className="public-cta" href="/get-started">شروع کنیم</a></header>
    <main>
      <nav className="public-breadcrumbs" aria-label="مسیر صفحه"><ol>{crumbs.map((crumb, index, list) => <li key={crumb.path}>{index === list.length - 1 ? <span aria-current="page">{crumb.title}</span> : <a href={crumb.path}>{crumb.title}</a>}</li>)}</ol></nav>
      <article>{path.startsWith("/exercise-library") ? <PublicExercises payload={payload} /> : tool ? <ToolHeader kind={tool.kind} /> : <><p className="public-eyebrow">دانش و ابزارهای فیتیشن</p><h1>{page.title}</h1><p className="public-lead">{page.description}</p></>}
        {page.article && <p className="public-attribution">ناشر: <a href="/about">فیتیشن</a> · انتشار: <time dateTime={page.published}>{page.published}</time> {page.updated && <> · به‌روزرسانی: <time dateTime={page.updated}>{page.updated}</time></>} · بازبینی مستقل متخصص ادعا نشده است.</p>}
        {tool && <Calculator kind={tool.kind} />}
        {path === "/tools" && <ToolHub />}
        {!path.startsWith("/exercise-library/") && page.sections.map(section => <section key={section.heading}><h2>{section.heading}</h2>{section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}</section>)}
        {page.references && <section><h2>منابع و دامنه شواهد</h2><p>منابع پژوهشی تضمین نتیجه فردی یا تأیید این صفحه توسط پژوهشگران نیستند.</p><ul>{page.references.map(ref => <li key={ref.url}><a href={ref.url} lang="en" dir="ltr">{ref.title}</a></li>)}</ul></section>}
        {related.length > 0 && <section><h2>مسیر بعدی مطالعه</h2><ul>{related.map(link => <li key={link.path}><a href={link.path}>{link.title}</a></li>)}</ul></section>}
        <aside className="public-next"><h2>برنامه متناسب با شرایط خودت</h2><p>هدف، زمان و امکاناتت را در مسیر شروع فیتیشن ثبت کن.</p><a className="public-cta" href="/get-started">ساخت برنامه شخصی در فیتیشن</a></aside>
      </article>
    </main><PublicDiscovery />
  </div>;
}
export function NotFound() {
  return <main className="public-knowledge public-not-found" lang="fa" dir="rtl"><h1>صفحه پیدا نشد</h1><p>این نشانی وجود ندارد یا دیگر منتشر نمی‌شود.</p><a href="/">بازگشت به فیتیشن</a><PublicDiscovery /></main>;
}
