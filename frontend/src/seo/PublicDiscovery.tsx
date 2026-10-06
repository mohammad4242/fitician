import { PublicFooter } from "./PublicShell";
const discoveries = [
  { path: "/workout-program", title: "برنامه تمرینی", description: "برنامه‌ریزی تمرین بر اساس هدف، سطح، زمان و امکانات.", icon: "training" },
  { path: "/nutrition", title: "تغذیه", description: "کالری، پروتئین و اصول تغذیه متناسب با مسیر تمرین.", icon: "nutrition" },
  { path: "/exercise-library", title: "کتابخانه حرکات", description: "حرکات را بر اساس عضله و تجهیزات پیدا کن و اجرای درست را ببین.", icon: "library" },
  { path: "/learn", title: "دانش فیتنس", description: "راهنماهای علمی و قابل‌فهم درباره تمرین، تغذیه و ریکاوری.", icon: "learn" },
  { path: "/tools", title: "ابزارها", description: "BMI، کالری روزانه و پروتئین موردنیاز را سریع محاسبه کن.", icon: "tools" },
  { path: "/body-analysis", title: "تحلیل بدن", description: "روند تغییرات بدنت را با یک نگاه ساختاریافته دنبال کن.", icon: "body" },
];
export function FeatureIcon({ kind }: { kind: string }) {
  const paths: Record<string, string> = {
    training: "M3 9v14m5-18v22m16-22v22m5-18v14M8 16h16",
    nutrition: "M16 7c-7-7-17 4-8 17 5 7 11 3 15-3 7-11 0-20-7-14Zm0 0c0-4 3-6 6-6M6 12h9",
    library: "M5 5h22v22H5zM11 5v22M17 11h5m-5 5h5m-5 5h3",
    learn: "M16 8c-4-4-9-4-13-2v21c4-2 9-2 13 2m0-21c4-4 9-4 13-2v21c-4-2-9-2-13 2V8",
    tools: "M7 3h18v26H7zM11 8h10M11 14h2m6 0h2m-10 5h2m6 0h2m-10 5h2m6 0h2",
    body: "M12 5a4 4 0 1 0 8 0 4 4 0 1 0-8 0m-2 8 6-2 6 2-2 8 3 9m-13-17 2 8-3 9m3-9h8",
  };
  return <svg viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={paths[kind] ?? paths.training} /></svg>;
}
export function PublicDiscovery() {
  return <div className="public-discovery" data-fitician-theme="dark" lang="fa" dir="rtl">
    <section className="discovery-section" aria-labelledby="public-discovery-title">
      <div className="discovery-heading"><p>FITICIAN / EXPLORE</p><h2 id="public-discovery-title" className="fitician-display">بیشتر از فیتیشن کشف کن</h2><span>از شناخت حرکت تا پیدا کردن مسیر خودت.</span></div>
      <div className="discovery-grid">{discoveries.map(item => <a className="discovery-card" href={item.path} key={item.path}>
        <span className="discovery-card-art"><FeatureIcon kind={item.icon} /></span>
        <h3 className="fitician-display">{item.title}</h3><p>{item.description}</p>
        <span className="discovery-card-link">کشف کن <span aria-hidden="true">←</span></span>
      </a>)}</div>
    </section><PublicFooter />
  </div>;
}
