import { PublicDiscovery } from "./PublicDiscovery";
import { Calculator } from "./Calculator";
import type { PublicPayload } from "./registry";
import { exerciseTaxonomy } from "./taxonomy";
import "./public.css";
export function PublicPage({ payload }: { payload: PublicPayload }) {
  const { page, exercise, crumbs, related, exerciseLinks } = payload;
  const path = page.path;
  return <div className="public-knowledge" lang="fa" dir="rtl">
    <header><a className="public-brand" href="/">Fitician <span>فیتیشن</span></a><a className="public-cta" href="/get-started">شروع کنیم</a></header>
    <main>
      <nav className="public-breadcrumbs" aria-label="مسیر صفحه"><ol>{crumbs.map((crumb, index, list) => <li key={crumb.path}>{index === list.length - 1 ? <span aria-current="page">{crumb.title}</span> : <a href={crumb.path}>{crumb.title}</a>}</li>)}</ol></nav>
      <article><p className="public-eyebrow">دانش و ابزارهای فیتیشن</p><h1>{page.title}</h1><p className="public-lead">{page.description}</p>
        {page.article && <p className="public-attribution">ناشر: <a href="/about">فیتیشن</a> · انتشار: <time dateTime={page.published}>{page.published}</time> {page.updated && <> · به‌روزرسانی: <time dateTime={page.updated}>{page.updated}</time></>} · بازبینی مستقل متخصص ادعا نشده است.</p>}
        {path === "/tools/calorie-calculator" && <Calculator />}
        {path === "/tools/protein-calculator" && <Calculator protein />}
        {page.sections.map(section => <section key={section.heading}><h2>{section.heading}</h2>{section.paragraphs.map(paragraph => <p key={paragraph}>{paragraph}</p>)}</section>)}
        {path === "/exercise-library" && <section><h2>حرکات منتخب</h2><ul className="public-grid">{exerciseLinks.map(record => <li key={record.path}><a href={record.path}>{record.title}</a><span lang="en" dir="ltr">{record.english}</span></li>)}</ul></section>}
        {exercise && <>
          <p lang="en" dir="ltr">{exercise.name_en}</p>
          <section><h2>راهنمای حرکت</h2><dl><dt>عضله اصلی</dt><dd>{exerciseTaxonomy[exercise.primary_muscle] ?? exercise.primary_muscle}</dd><dt>عضلات کمکی</dt><dd>{exercise.secondary_muscles.map(value => exerciseTaxonomy[value] ?? value).join("، ") || "ثبت نشده"}</dd><dt>تأکید عضلانی</dt><dd>{exercise.muscle_focus ? exerciseTaxonomy[exercise.muscle_focus] ?? exercise.muscle_focus : "ثبت نشده"}</dd><dt>تجهیزات</dt><dd>{exercise.equipment.map(value => exerciseTaxonomy[value] ?? value).join("، ")}</dd><dt>سطح دشواری</dt><dd>{exerciseTaxonomy[exercise.difficulty] ?? exercise.difficulty}</dd></dl></section>
          <section><h2>روش اجرای حرکت</h2><ol>{exercise.instructions_fa.map(instruction => <li key={instruction}>{instruction}</li>)}</ol></section>
          <section><h2>نکات فرم و ایمنی</h2><ul>{exercise.safety_notes_fa.map(note => <li key={note}>{note}</li>)}</ul><p>این راهنما از مجموعه پایه کاتالوگ فیتیشن است؛ ارزیابی فرم یا درمان آسیب نیست. در صورت درد تیز یا علائم غیرمعمول تمرین را متوقف کن و ارزیابی مناسب بگیر.</p></section>
          <section><h2>حرکات مرتبط با همین عضله</h2><ul>{exerciseLinks.map(record => <li key={record.path}><a href={record.path}>{record.title}</a></li>)}</ul></section>
        </>}
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
