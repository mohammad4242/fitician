import { useState } from "react";
import { BrandLogo } from "../shared/BrandLogo";

const navigation = [
  ["/workout-program", "تمرین"], ["/nutrition", "تغذیه"],
  ["/exercise-library", "حرکات"], ["/learn", "دانش فیتنس"], ["/tools", "ابزارها"],
];
export function PublicHeader({ path }: { path: string }) {
  const [open, setOpen] = useState(false);
  return <header className="public-header" onKeyDown={event => {
    if (event.key === "Escape") setOpen(false);
  }}>
    <div className="public-header-inner">
      <a className="public-logo" href="/" aria-label="فیتیشن"><BrandLogo /></a>
      <nav className="public-main-nav" id="public-main-navigation" aria-label="ناوبری فیتیشن" data-open={open}>
        {navigation.map(([href, name]) => <a href={href} key={href} onClick={() => setOpen(false)}
          aria-current={path === href || path.startsWith(`${href}/`) ? "page" : undefined}>{name}</a>)}
      </nav>
      <div className="public-header-actions"><a className="public-login" href="/login">ورود</a>
        <a className="public-cta" href="/get-started">شروع فیتیشن</a>
        <button className="public-menu-toggle" type="button" aria-label="منوی فیتیشن"
          aria-controls="public-main-navigation" aria-expanded={open} onClick={() => setOpen(value => !value)}>
          <span aria-hidden="true">{open ? "×" : "☰"}</span>
        </button>
      </div>
    </div>
  </header>;
}
const groups = [
  { title: "محصول", links: [["/workout-program", "تمرین"], ["/nutrition", "تغذیه"], ["/body-analysis", "تحلیل بدن"], ["/tools", "ابزارها"], ["/exercise-library", "حرکات"]] },
  { title: "دانش", links: [["/learn", "دانش فیتنس"], ["/editorial-policy", "سیاست تحریریه"]] },
  { title: "فیتیشن", links: [["/about", "درباره ما"], ["/support", "پشتیبانی"], ["/privacy", "حریم خصوصی"], ["/install", "نصب برنامه"]] },
];
export function PublicFooter() {
  return <footer className="public-footer" data-fitician-theme="dark" lang="fa" dir="rtl">
    <div className="public-footer-inner">
      <div className="public-footer-brand"><a className="public-logo" href="/" aria-label="فیتیشن"><BrandLogo /></a>
        <p>تمرین، تغذیه و پیگیری روند؛<br />متناسب با زندگی واقعی تو.</p>
        <a className="public-footer-start" href="/get-started">شروع فیتیشن <span aria-hidden="true">←</span></a>
      </div>
      {groups.map(group => <nav key={group.title} aria-label={group.title}><h2>{group.title}</h2>
        {group.links.map(([href, label]) => <a href={href} key={href}>{label}</a>)}
      </nav>)}
    </div>
    <div className="public-footer-base"><span>Fitician · Fit with Science</span><span>آموزش عمومی؛ جایگزین ارزیابی حرفه‌ای نیست.</span></div>
  </footer>;
}
export function PublicProgramCta({ exercise = false, workout = false }: { exercise?: boolean; workout?: boolean }) {
  return <aside className="public-next"><div><p className="public-eyebrow">مسیر شخصی تو</p>
    <h2 className="fitician-display">{exercise ? "برنامه‌ای می‌خواهی که این حرکات را متناسب با بدنت بچیند؟" : "از شناختن مسیر، به برنامه خودت برس"}</h2>
    <p>هدف، زمان و امکاناتت را ثبت کن؛ برنامه‌ات از شرایط خودت شروع می‌شود.</p></div>
    <a className="public-cta" href="/get-started">{workout ? "برنامه تمرینی مخصوص من" : "شروع فیتیشن"}<span aria-hidden="true"> ←</span></a>
  </aside>;
}
