import { Calculator } from "./Calculator";
import { ToolHeader, ToolHub } from "./Tools";
import { tools } from "./tools";
import type { PublicPayload } from "./registry";
import { PublicFooter, PublicHeader, PublicProgramCta } from "./PublicShell";
import { TopicExperience, TopicHero } from "./TopicExperiences";
import "./public.css";

const topicPaths = new Set(["/workout-program", "/nutrition", "/body-analysis", "/learn", "/about"]);
export function PublicPage({ payload, exerciseContent }: { payload: PublicPayload; exerciseContent?: React.ReactNode }) {
  const { page, crumbs, related } = payload;
  const path = page.path;
  const tool = tools.find(tool => tool.path === path);
  const exercise = path.startsWith("/exercise-library");
  const topic = topicPaths.has(path);
  return <div className={`public-knowledge ${exercise ? "public-exercise-page" : topic ? "public-topic-page" : page.article ? "public-article-page" : "public-tool-page"}`} data-fitician-theme="dark" lang="fa" dir="rtl">
    <a className="public-skip-link" href="#public-content">رفتن به محتوا</a>
    <PublicHeader path={path} />
    <main id="public-content">
      <nav className="public-breadcrumbs" aria-label="مسیر صفحه"><ol>{crumbs.map((crumb, index, list) => <li key={crumb.path}>
        {index === list.length - 1 ? <span aria-current="page">{crumb.title}</span> : <a href={crumb.path}>{crumb.title}</a>}
      </li>)}</ol></nav>
      <div className="public-page-content">
        {exercise ? exerciseContent : topic ? <TopicExperience payload={payload} /> : <>
          {tool ? <ToolHeader kind={tool.kind} /> : <TopicHero eyebrow={page.article ? "FITICIAN / KNOWLEDGE" : "FITICIAN / TOOLS & KNOWLEDGE"} title={page.title} description={page.description} />}
          {page.article && <p className="public-attribution">ناشر: <a href="/about">فیتیشن</a> · انتشار: <time dateTime={page.published}>{page.published}</time>
            {page.updated && <> · به‌روزرسانی: <time dateTime={page.updated}>{page.updated}</time></>} · بازبینی مستقل متخصص ادعا نشده است.</p>}
          {tool && <Calculator kind={tool.kind} />}
          {path === "/tools" && <ToolHub />}
          <article className="public-reading-content">{page.sections.map((section, index) => <section key={section.heading} id={`section-${index}`}>
            <h2 className="fitician-display">{section.heading}</h2>{section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}
          </section>)}</article>
        </>}
        {exercise && !payload.exercise && <p className="public-library-note">حرکت را قبل از اجرا بشناس. آموزش عمومی جای مشاهده فرم توسط مربی یا ارزیابی محدودیت فردی را نمی‌گیرد.</p>}
        {page.references && <section className="public-references"><h2>منابع و دامنه شواهد</h2><p>منابع پژوهشی تضمین نتیجه فردی یا تأیید این صفحه توسط پژوهشگران نیستند.</p>
          <ul>{page.references.map(ref => <li key={ref.url}><a href={ref.url} lang="en" dir="ltr">{ref.title}</a></li>)}</ul>
        </section>}
        {related.length > 0 && <section className="public-related"><h2 className="fitician-display">مسیر بعدی</h2><div className="public-related-grid">
          {related.map(link => <a href={link.path} key={link.path}>{link.title}<span aria-hidden="true">←</span></a>)}
        </div></section>}
        <PublicProgramCta exercise={exercise} workout={path === "/workout-program"} />
      </div>
    </main><PublicFooter />
  </div>;
}
export function NotFound() {
  return <div className="public-knowledge" data-fitician-theme="dark" lang="fa" dir="rtl"><PublicHeader path="/404" />
    <main className="public-not-found"><h1>صفحه پیدا نشد</h1><p>این نشانی وجود ندارد یا دیگر منتشر نمی‌شود.</p><a href="/">بازگشت به فیتیشن</a></main><PublicFooter />
  </div>;
}
