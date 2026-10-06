import { BrandLogo } from "../shared/BrandLogo";
import type { PublicPayload } from "./registry";
import type { PublicPage as Page, Section } from "./content";
import { FeatureIcon } from "./PublicDiscovery";

export function TopicHero({ eyebrow, title, description, children }: {
  eyebrow: string; title: string; description: string; children?: React.ReactNode;
}) {
  return <header className="public-topic-hero"><div><p className="public-eyebrow">{eyebrow}</p>
    <h1 className="fitician-display">{title}</h1><p className="public-lead">{description}</p></div>{children}</header>;
}
function SectionCards({ sections }: { sections: Section[] }) {
  return <div className="public-insight-grid">{sections.map((section, index) => <section className="public-insight-card" key={section.heading}
    id={section.heading.includes("ریکاوری") ? "recovery" : `insight-${index}`}>
    <h2 className="fitician-display">{section.heading}</h2><p>{section.paragraphs[0]}</p>
    {section.paragraphs.length > 1 && <details className="public-reading-detail"><summary>بیشتر بدان</summary>
      {section.paragraphs.slice(1).map(text => <p key={text}>{text}</p>)}
    </details>}
  </section>)}</div>;
}
const inputs = [
  ["هدف", "قدرت، عضله‌سازی یا مدیریت وزن"], ["سطح تمرین", "تجربه و توان اجرای حرکت"],
  ["روزهای در دسترس", "هفته‌ای که واقعاً می‌توانی ادامه بدهی"], ["زمان جلسه", "متناسب با زمان روزمره"],
  ["تجهیزات", "خانه یا باشگاه"], ["ریکاوری", "توزیع فشار و فرصت بازیابی"],
];
function WorkoutExperience({ page }: { page: Page }) {
  return <div className="public-workout">
    <TopicHero eyebrow="FITICIAN / TRAINING" title="برنامه تمرینی فقط یک لیست حرکت نیست" description={page.description}>
      <div className="training-blueprint"><p className="blueprint-label">منطق یک برنامه شخصی</p>
        <dl>{inputs.map(([name, detail]) => <div key={name}><dt>{name}</dt><dd>{detail}</dd></div>)}</dl>
        <div className="blueprint-output"><FeatureIcon kind="training" /><span>حجم · تناوب · تقسیم جلسات</span></div>
      </div>
    </TopicHero>
    <section className="public-splits" aria-labelledby="split-heading"><div className="public-section-heading">
      <p className="public-eyebrow">ساختار تمرین</p><h2 id="split-heading" className="fitician-display">نام برنامه، نقطه شروع نیست</h2>
      <p>تقسیم جلسات را بعد از شناخت هدف، روزها و توان بازیابی انتخاب کن. این‌ها ساختارند؛ نسخه آماده نیستند.</p>
    </div><div className="public-split-grid">
      {[
        { name: "Full Body", title: "تمام‌بدن", blocks: ["پایین‌تنه", "پرس", "کشش"], text: "چند گروه عضلانی در یک جلسه؛ یک ساختار قابل بررسی برای هفته‌های کم‌جلسه.", path: "/learn/beginner-training" },
        { name: "Upper / Lower", title: "بالاتنه / پایین‌تنه", blocks: ["بالاتنه", "پایین‌تنه"], text: "توزیع کار میان جلسات بالاتنه و پایین‌تنه؛ هماهنگ با تعداد روزهای قابل‌تداوم.", path: "/learn/upper-lower" },
        { name: "Push / Pull / Legs", title: "فشار / کشش / پا", blocks: ["فشار", "کشش", "پا"], text: "سازمان‌دهی بر اساس الگوی حرکت؛ نام آن تضمین رشد بیشتر یا مناسب بودن برای همه نیست.", path: "/exercise-library" },
      ].map(split => <article className="public-split-card" key={split.name}><p className="public-utility" lang="en" dir="ltr">{split.name}</p>
        <h3 className="fitician-display">{split.title}</h3><div className="split-blocks">{split.blocks.map(block => <span key={block}>{block}</span>)}</div>
        <p>{split.text}</p><a href={split.path}>ساختار را بشناس <span aria-hidden="true">←</span></a>
      </article>)}
    </div></section>
    <SectionCards sections={page.sections} />
  </div>;
}
function NutritionExperience({ page }: { page: Page }) {
  return <div className="public-nutrition">
    <TopicHero eyebrow="FITICIAN / NUTRITION" title="تغذیه‌ای که بتوانی ادامه بدهی" description={page.description}>
      <div className="nutrition-composition"><FeatureIcon kind="nutrition" /><p>یک عدد، تمام تغذیه نیست</p>
        <div><strong>انرژی</strong><span>متناسب با هدف</span></div><div><strong>پروتئین</strong><span>در وعده‌های واقعی</span></div>
        <div><strong>کیفیت و تنوع</strong><span>هماهنگ با زندگی تو</span></div>
      </div>
    </TopicHero>
    <section className="public-nutrition-tools" aria-labelledby="nutrition-tools-heading"><h2 id="nutrition-tools-heading" className="fitician-display">یک برآورد شفاف برای شروع</h2>
      <div className="public-link-grid">{[
        ["/tools/calorie-calculator", "کالری روزانه", "برآورد انرژی؛ نقطه شروع برای دنبال کردن روند، نه یک نسخه درمانی."],
        ["/tools/protein-calculator", "پروتئین روزانه", "بازه آموزشی پروتئین برای بزرگسال سالم و فعال."],
        ["/tools/bmi-calculator", "شاخص BMI", "وزن نسبت به قد؛ همراه با محدودیت‌های روشن."],
      ].map(([path, title, description]) => <a className="public-content-link" href={path} key={path}><FeatureIcon kind="tools" /><h3>{title}</h3><p>{description}</p><span>محاسبه کن ←</span></a>)}</div>
    </section><SectionCards sections={page.sections} />
    <a className="public-reading-link" href="/learn/protein">راهنمای پروتئین: از بازه پژوهشی تا غذای روزمره ←</a>
  </div>;
}
function BodyExperience({ page }: { page: Page }) {
  return <div className="public-body">
    <TopicHero eyebrow="FITICIAN / BODY INTELLIGENCE" title="تغییرات بدنت را در مسیر ببین" description={page.description}>
      <div className="body-capture-diagram" role="img" aria-label="طرح مفهومی ثبت تصاویر با زاویه و نور ثابت؛ تصویر کاربر نیست">
        <div className="body-capture-frame"><FeatureIcon kind="body" /><span>ثبت منظم</span></div>
        <div className="capture-conditions"><span>نور ثابت</span><span>زاویه ثابت</span><span>فاصله ثابت</span></div>
        <p>شرایط مشابه، مقایسه معنادارتر</p>
      </div>
    </TopicHero>
    <ol className="public-process"><li><span>۱</span><h2>ورودی تو</h2><p>تصاویر و اطلاعاتی که در حساب خودت ثبت می‌کنی؛ با شرایط ثبت تا حد ممکن مشابه.</p></li>
      <li><span>۲</span><h2>نگاه ساختاریافته</h2><p>سازمان‌دهی تصاویر و برآورد نرم‌افزاری؛ برای مشاهده روند، با توجه به محدودیت‌های تصویر.</p></li>
      <li><span>۳</span><h2>پیگیری تغییرات</h2><p>تصویر را کنار عملکرد تمرین و اندازه‌گیری‌ها ببین؛ ظاهر، تمام وضعیت سلامت نیست.</p></li></ol>
    <div className="public-boundary"><FeatureIcon kind="body" /><div><h2>پیگیری روند، با مرز روشن</h2><p>این تجربه تشخیص بیماری، درمان آسیب یا اندازه‌گیری قطعی درصد چربی نیست.</p></div></div>
    <SectionCards sections={page.sections} /><a className="public-reading-link" href="/privacy">تصاویر خصوصی و کنترل اطلاعاتت را بشناس ←</a>
  </div>;
}
function ArticleCard({ article, featured = false }: { article: Page; featured?: boolean }) {
  return <a className={`learn-article-card${featured ? " learn-article-featured" : ""}`} href={article.path}>
    <div className="learn-article-art" aria-hidden="true"><FeatureIcon kind={article.path.endsWith("protein") ? "nutrition" : "training"} /></div>
    <div className="learn-article-body"><p className="public-eyebrow">{article.path.endsWith("protein") ? "تغذیه" : "تمرین"}{featured ? " · پیشنهاد برای شروع" : ""}</p>
      <h2 className="fitician-display">{article.title}</h2><p>{article.description}</p>
      <div className="learn-article-meta"><span>راهنمای کاربردی · با منابع مشخص</span>{article.published && <time dateTime={article.published}>{new Intl.DateTimeFormat("fa-IR", { timeZone: "UTC", dateStyle: "medium" }).format(new Date(article.published))}</time>}</div>
      <span className="learn-article-action">راهنما را بخوان <span aria-hidden="true">←</span></span>
    </div>
  </a>;
}
function LearnExperience({ payload }: { payload: PublicPayload }) {
  const articles = payload.articles ?? [];
  return <div className="public-learn"><TopicHero eyebrow="FITICIAN / KNOWLEDGE" title="برای تصمیم بهتر، بیشتر بدان" description={payload.page.description} />
    <nav className="learn-topic-nav" aria-label="موضوع‌های دانش"><a href="#training">تمرین</a><a href="#nutrition">تغذیه</a><a href="#recovery">ریکاوری</a><a href="/editorial-policy">منابع و روش علمی</a></nav>
    {articles[0] && <ArticleCard article={articles[0]} featured />}
    <section id="training" className="learn-topic-group"><div className="public-section-heading"><p className="public-eyebrow">TRAINING</p><h2 className="fitician-display">تمرین؛ از شروع تا ساختار</h2></div>
      <div className="learn-article-grid">{articles.filter(article => !article.path.endsWith("protein")).map(article => <ArticleCard key={article.path} article={article} />)}</div>
    </section>
    <section id="nutrition" className="learn-topic-group"><div className="public-section-heading"><p className="public-eyebrow">NUTRITION</p><h2 className="fitician-display">تغذیه؛ از عدد تا وعده</h2></div>
      <div className="learn-article-grid">{articles.filter(article => article.path.endsWith("protein")).map(article => <ArticleCard key={article.path} article={article} />)}</div>
    </section>
    <section id="recovery" className="learn-recovery"><FeatureIcon kind="body" /><div><p className="public-eyebrow">RECOVERY</p><h2 className="fitician-display">ریکاوری، بخشی از برنامه است</h2><p>خواب، تغذیه و فاصله جلسات را کنار روند عملکردت ببین.</p><a href="/workout-program#recovery">بخش پیشرفت و ریکاوری را بخوان ←</a></div></section>
    <SectionCards sections={payload.page.sections} />
  </div>;
}
function AboutExperience({ page }: { page: Page }) {
  return <div className="public-about"><TopicHero eyebrow="FITICIAN / FIT WITH SCIENCE" title="فیتیشن؛ برای یک مسیر قابل‌تداوم" description={page.description}>
    <div className="about-brand-panel"><BrandLogo /><p>تمرین · تغذیه · پیگیری روند</p><span>شرایط تو، نقطه شروع برنامه تو.</span></div>
  </TopicHero>
    <section className="about-purpose"><p className="public-eyebrow">چرا فیتیشن؟</p><h2 className="fitician-display">زندگی واقعی، برنامه واقعی می‌خواهد</h2><p>هدف، تجربه، روزهای در دسترس و امکانات افراد یکسان نیست. فیتیشن این شرایط را در مسیر ساخت برنامه ثبت می‌کند و تمرین، تغذیه و پیگیری روند را در یک تجربه کنار هم می‌آورد.</p></section>
    <div className="about-principles">{[
      ["شخصی‌سازی از شرایط تو", "برنامه‌ریزی نرم‌افزاری بر اساس اطلاعاتی که ثبت می‌کنی؛ با امکان دنبال کردن روند در حساب."],
      ["شواهد، همراه با محدودیت‌ها", "آموزش عمومی با منابع مشخص؛ بدون تضمین نتیجه فردی یا ادعای بازبینی تخصصی انجام‌نشده."],
      ["داده شخصی، در حساب شخصی", "تصاویر بدن در بخش عمومی منتشر نمی‌شوند. دسترسی و حذف اطلاعات را در سیاست حریم خصوصی بشناس."],
      ["نرم‌افزار و متخصص", "ابزار می‌تواند برنامه و روند را سازمان‌دهی کند؛ تشخیص پزشکی و ارزیابی حرفه‌ای جای خود را دارند."],
    ].map(([title, text]) => <section key={title}><h2 className="fitician-display">{title}</h2><p>{text}</p></section>)}</div>
    <SectionCards sections={page.sections} /><div className="about-trust-links"><a href="/editorial-policy">سیاست تحریریه ←</a><a href="/privacy">حریم خصوصی ←</a><a href="/support">گفت‌وگو با پشتیبانی ←</a></div>
  </div>;
}
export function TopicExperience({ payload }: { payload: PublicPayload }) {
  switch (payload.page.path) {
    case "/workout-program": return <WorkoutExperience page={payload.page} />;
    case "/nutrition": return <NutritionExperience page={payload.page} />;
    case "/body-analysis": return <BodyExperience page={payload.page} />;
    case "/learn": return <LearnExperience payload={payload} />;
    case "/about": return <AboutExperience page={payload.page} />;
    default: return null;
  }
}
