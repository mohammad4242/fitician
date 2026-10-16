import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BrandLogo } from "../../shared/BrandLogo";
import { LanguageSwitcher } from "../../shared/LanguageSwitcher";
import { usePwaInstall } from "../../pwa/usePwaInstall";
import { detectInstallEnvironment, detectInstallPlatform, type InstallPlatform } from "./installEnvironment";
import "./publicInstall.css";

type Language = "fa" | "en";
type StepIconName = "share" | "home" | "web-app" | "add";

type InstallStep = {
  icon: StepIconName;
  content: ReactNode;
};

const installCopy: Record<Language, {
  eyebrow: string;
  heroTitle: string;
  installedTitle: string;
  heroDescription: string;
  installedDescription: string;
  iosTitle: string;
  iosDescription: string;
  iosSteps: InstallStep[];
  instagramTitle: string;
  instagramDescription: string;
  instagramSteps: string[];
  copyLink: string;
  copied: string;
  copyFailed: string;
  installedMessage: string;
  chromiumTitle: string;
  chromiumDescription: string;
  installAction: string;
  installError: string;
  continueAction: string;
}> = {
  fa: {
    eyebrow: "همراه تمرین و تغذیهٔ تو",
    heroTitle: "فیتیشن رو نصب کن",
    installedTitle: "فیتیشن روی دستگاهت نصب شده",
    heroDescription: "روی اندروید یا آیفون؛ همیشه دم دست.",
    installedDescription: "فیتیشن آماده است؛ از آیکن روی صفحهٔ اصلی بازش کن.",
    iosTitle: "نصب فیتیشن روی صفحهٔ اصلی",
    iosDescription: "در Safari این چهار قدم را انجام بده:",
    iosSteps: [
      {
        icon: "share",
        content: <>در <bdi dir="ltr">Safari</bdi> روی دکمهٔ <bdi dir="ltr">Share</bdi> بزن.</>,
      },
      {
        icon: "home",
        content: <>گزینهٔ <bdi dir="ltr">Add to Home Screen</bdi> را انتخاب کن.</>,
      },
      {
        icon: "web-app",
        content: <>اگر گزینهٔ <bdi dir="ltr">Open as Web App</bdi> نمایش داده شد، روشن نگهش دار.</>,
      },
      {
        icon: "add",
        content: <>در پایان <bdi dir="ltr">Add</bdi> را بزن.</>,
      },
    ],
    instagramTitle: "یک قدم تا نصب فیتیشن",
    instagramDescription: "این صفحه داخل مرورگر اینستاگرام باز شده. برای نصب، اول فیتیشن را در Safari یا مرورگر اصلی باز کن.",
    instagramSteps: [
      "منوی مرورگر اینستاگرام را باز کن.",
      "گزینهٔ «Open in Safari» یا «Open in Browser» را انتخاب کن.",
      "بعد از باز شدن صفحه در Safari، مراحل نصب پایین صفحه را انجام بده.",
    ],
    copyLink: "کپی لینک",
    copied: "لینک کپی شد ✓",
    copyFailed: "کپی خودکار در دسترس نیست؛ لینک صفحه را از نوار آدرس کپی کن.",
    installedMessage: "برای ورود، فیتیشن را از صفحهٔ اصلی دستگاهت باز کن یا ادامه بده در مرورگر.",
    chromiumTitle: "فیتیشن را به صفحهٔ اصلی اضافه کن",
    chromiumDescription: "مرورگرت آمادهٔ نصب فیتیشن است. با تأیید پنجرهٔ نصب، آیکن فیتیشن به دستگاهت اضافه می‌شود.",
    installAction: "نصب فیتیشن",
    installError: "مرورگر نتوانست پنجرهٔ نصب را باز کند. فیتیشن را می‌توانی در همین مرورگر ادامه بدهی.",
    continueAction: "ورود به فیتیشن",
  },
  en: {
    eyebrow: "Your training and nutrition companion",
    heroTitle: "Install Fitician",
    installedTitle: "Fitician is installed on this device",
    heroDescription: "On Android or iPhone. Always close at hand.",
    installedDescription: "Fitician is ready. Open it from the icon on your Home Screen.",
    iosTitle: "Install Fitician on your Home Screen",
    iosDescription: "In Safari, follow these four steps:",
    iosSteps: [
      { icon: "share", content: <>In <bdi dir="ltr">Safari</bdi>, tap <bdi dir="ltr">Share</bdi>.</> },
      { icon: "home", content: <>Choose <bdi dir="ltr">Add to Home Screen</bdi>.</> },
      { icon: "web-app", content: <>If <bdi dir="ltr">Open as Web App</bdi> appears, leave it enabled.</> },
      { icon: "add", content: <>Tap <bdi dir="ltr">Add</bdi> to finish.</> },
    ],
    instagramTitle: "One step away from Fitician",
    instagramDescription: "This page opened inside Instagram. First open Fitician in Safari or your main browser to install it.",
    instagramSteps: [
      "Open the browser menu in Instagram.",
      "Choose “Open in Safari” or “Open in Browser.”",
      "Once the page opens in Safari, follow the install steps below.",
    ],
    copyLink: "Copy link",
    copied: "Link copied ✓",
    copyFailed: "Automatic copying is unavailable. Copy this page's link from the address bar.",
    installedMessage: "Open Fitician from your Home Screen, or continue in the browser.",
    chromiumTitle: "Add Fitician to your Home Screen",
    chromiumDescription: "Your browser can install Fitician now. Confirm its install prompt to add the app icon to this device.",
    installAction: "Install Fitician",
    installError: "Your browser could not open the install prompt. You can keep using Fitician in this browser.",
    continueAction: "Go to Fitician",
  },
};

export function PublicInstallPage() {
  const { i18n } = useTranslation();
  const language: Language = i18n.resolvedLanguage === "en" ? "en" : "fa";
  const copy = installCopy[language];
  const { state: pwaState, canPrompt, install } = usePwaInstall();
  const [copyStatus, setCopyStatus] = useState<"copied" | "failed" | null>(null);
  const [installFailed, setInstallFailed] = useState(false);
  const browserNavigator = typeof navigator === "undefined" ? undefined : navigator;
  const navigatorWithStandalone = browserNavigator as (Navigator & { standalone?: boolean }) | undefined;
  const environment = detectInstallEnvironment({
    userAgent: browserNavigator?.userAgent ?? "",
    platform: browserNavigator?.platform,
    maxTouchPoints: browserNavigator?.maxTouchPoints,
    standalone: navigatorWithStandalone?.standalone === true,
    displayModeStandalone: typeof window !== "undefined" && window.matchMedia?.("(display-mode: standalone)").matches === true,
    canPrompt,
    pwaState,
  });

  const [selectedPlatform, setSelectedPlatform] = useState<InstallPlatform>(() => detectInstallPlatform({
    userAgent: browserNavigator?.userAgent ?? "",
    platform: browserNavigator?.platform,
    maxTouchPoints: browserNavigator?.maxTouchPoints,
  }));

  function selectPlatform(platform: InstallPlatform) {
    setSelectedPlatform(platform);
    setCopyStatus(null);
    setInstallFailed(false);
  }

  useEffect(() => {
    if (copyStatus === null) return;
    const timeout = window.setTimeout(() => setCopyStatus(null), 2600);
    return () => window.clearTimeout(timeout);
  }, [copyStatus]);

  async function copyCurrentLink() {
    try {
      if (navigator.clipboard?.writeText === undefined) throw new Error("Clipboard unavailable");
      await navigator.clipboard.writeText(window.location.href);
      setCopyStatus("copied");
    } catch {
      setCopyStatus("failed");
    }
  }

  async function promptInstallation() {
    try {
      setInstallFailed(false);
      await install();
    } catch {
      setInstallFailed(true);
    }
  }

  function showIosInstructions() {
    const title = document.getElementById(environment === "ios-in-app-browser"
      ? "public-install-handoff-title" : "public-install-steps-title");
    title?.focus({ preventScroll: true });
    title?.scrollIntoView({ block: "start" });
  }

  const heroTitle = environment === "installed" ? copy.installedTitle : copy.heroTitle;
  const heroDescription = environment === "installed" ? copy.installedDescription : copy.heroDescription;

  return (
    <main className="public-install" dir={language === "fa" ? "rtl" : "ltr"} lang={language}>
      <div className="public-install__shell">
        <header className="public-install__header">
          <LanguageSwitcher />
        </header>

        <div className="public-install__layout">
          <section className="public-install__hero" aria-labelledby="public-install-title">
            <p className="public-install__eyebrow">{copy.eyebrow}</p>
            <BrandLogo className="public-install__logo" testId="public-install-brand-logo" />
            <h1 className="public-install__title fitician-display" id="public-install-title">
              {heroTitle}
              {environment === "installed" && <span aria-hidden="true"> ✓</span>}
            </h1>
            <p className="public-install__hero-description">{heroDescription}</p>
          </section>

          <div className="public-install__content">
            <div className="public-install__tabs" role="tablist" aria-label={language === "fa" ? "انتخاب دستگاه" : "Choose your device"}>
              {(["android", "iphone"] as const).map((platform) => (
                <button key={platform} id={`install-tab-${platform}`} type="button" role="tab"
                  className="public-install__tab" aria-selected={selectedPlatform === platform}
                  aria-controls={`install-panel-${platform}`} tabIndex={selectedPlatform === platform ? 0 : -1}
                  onClick={() => selectPlatform(platform)}
                  onKeyDown={(event) => {
                    if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
                    event.preventDefault();
                    const next = event.key === "Home" ? "android" : event.key === "End" ? "iphone" : platform === "android" ? "iphone" : "android";
                    selectPlatform(next);
                    document.getElementById(`install-tab-${next}`)?.focus();
                  }}>
                  <PlatformIcon platform={platform} />
                  <span>{platform === "android" ? (language === "fa" ? "اندروید" : "Android") : (language === "fa" ? "آیفون" : "iPhone")}</span>
                </button>
              ))}
            </div>
            <div hidden role="tabpanel" id={`install-panel-${selectedPlatform === "android" ? "iphone" : "android"}`} aria-labelledby={`install-tab-${selectedPlatform === "android" ? "iphone" : "android"}`} />
            <div key={selectedPlatform} className="public-install__platform-panel" role="tabpanel"
              id={`install-panel-${selectedPlatform}`} aria-labelledby={`install-tab-${selectedPlatform}`} tabIndex={0}>
              {selectedPlatform === "android" && (
                <div className="public-install__downloads">
                  <a className="public-install__button" href="/download/android">
                    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5" /></svg>
                    {language === "fa" ? "دانلود مستقیم APK" : "Download APK"}
                  </a>
                  <button className="public-install__button public-install__button--quiet" type="button" disabled>
                    {language === "fa" ? "دریافت از کافه بازار" : "Cafe Bazaar"}<small>{language === "fa" ? "به‌زودی" : "Coming soon"}</small>
                  </button>
                  <button className="public-install__button public-install__button--quiet" type="button" disabled>
                    {language === "fa" ? "دریافت از مایکت" : "Myket"}<small>{language === "fa" ? "به‌زودی" : "Coming soon"}</small>
                  </button>
                </div>
              )}
              {selectedPlatform === "iphone" && environment !== "installed" && (
                <button className="public-install__button" type="button" onClick={showIosInstructions}>
                  <StepIcon name="add" />{language === "fa" ? "نصب وب‌اپلیکیشن فیتیشن" : "Install Fitician web app"}
                </button>
              )}
              {selectedPlatform === "iphone" && environment === "ios-in-app-browser" && (
                <section className="public-install__panel public-install__panel--handoff" aria-labelledby="public-install-handoff-title">
                  <div className="public-install__panel-heading">
                    <span className="public-install__panel-mark" aria-hidden="true"><StepIcon name="share" /></span>
                    <div>
                      <p className="public-install__section-kicker">{language === "fa" ? "اول مرورگر اصلی" : "FIRST, YOUR MAIN BROWSER"}</p>
                      <h2 id="public-install-handoff-title" tabIndex={-1}>{copy.instagramTitle}</h2>
                    </div>
                  </div>
                  <p className="public-install__panel-description">{copy.instagramDescription}</p>
                  <ol className="public-install__handoff-steps">
                    {copy.instagramSteps.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                  <div className="public-install__copy-action">
                    <button className="public-install__button public-install__button--quiet" type="button" onClick={() => void copyCurrentLink()}>
                      <CopyIcon />
                      {copy.copyLink}
                    </button>
                    <p className="public-install__status" role="status" aria-live="polite" aria-atomic="true">
                      {copyStatus === "copied" ? copy.copied : copyStatus === "failed" ? copy.copyFailed : ""}
                    </p>
                  </div>
                </section>
              )}

              {selectedPlatform === "iphone" && environment !== "installed" && (
                <section className="public-install__panel public-install__panel--steps" aria-labelledby="public-install-steps-title">
                  <div className="public-install__panel-heading">
                    <span className="public-install__panel-mark public-install__panel-mark--steps" aria-hidden="true">4</span>
                    <div>
                      <p className="public-install__section-kicker">{language === "fa" ? "نصب از Safari" : "FROM SAFARI"}</p>
                      <h2 id="public-install-steps-title" tabIndex={-1}>{copy.iosTitle}</h2>
                    </div>
                  </div>
                  <p className="public-install__panel-description">{copy.iosDescription}</p>
                  <ol className="public-install__steps">
                    {copy.iosSteps.map((step, index) => (
                      <li className="public-install__step" key={step.icon}>
                        <span className="public-install__step-number" aria-hidden="true">{index + 1}</span>
                        <span className="public-install__step-icon"><StepIcon name={step.icon} /></span>
                        <span className="public-install__step-copy">{step.content}</span>
                      </li>
                    ))}
                  </ol>
                </section>
              )}

              {environment === "installed" && (
                <section className="public-install__panel public-install__panel--state" aria-labelledby="public-install-state-title">
                  <span className="public-install__success-mark" aria-hidden="true">✓</span>
                  <div>
                    <h2 id="public-install-state-title">{copy.installedMessage}</h2>
                  </div>
                </section>
              )}

              {selectedPlatform === "android" && environment === "chromium-prompt" && (
                <section className="public-install__panel public-install__panel--state" aria-labelledby="public-install-state-title">
                  <span className="public-install__panel-mark" aria-hidden="true"><StepIcon name="add" /></span>
                  <div>
                    <p className="public-install__section-kicker">{language === "fa" ? "آمادهٔ نصب" : "READY TO INSTALL"}</p>
                    <h2 id="public-install-state-title">{copy.chromiumTitle}</h2>
                    <p className="public-install__panel-description">{copy.chromiumDescription}</p>
                    {installFailed && <p className="public-install__error" role="alert">{copy.installError}</p>}
                    <button className="public-install__button" type="button" onClick={() => void promptInstallation()}>
                      {copy.installAction}
                    </button>
                  </div>
                </section>
              )}

            </div>
            <Link className="public-install__browser-link" to="/">{copy.continueAction}</Link>
          </div>
        </div>

        <footer className="public-install__footer">
          <span className="public-install__footer-dot" aria-hidden="true" />
          <span>{language === "fa" ? "فیتیشن؛ همراه تمرین و تغذیهٔ تو" : "Fitician, alongside your training and nutrition"}</span>
        </footer>
      </div>
    </main>
  );
}

function StepIcon({ name }: { name: StepIconName }) {
  if (name === "share") {
    return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 15V3m0 0L8 7m4-4 4 4M5 13v7h14v-7" /></svg>;
  }
  if (name === "home") {
    return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1zM9 21v-7h6v7" /></svg>;
  }
  if (name === "web-app") {
    return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="3" y="4" width="18" height="16" rx="3" /><path d="M3 9h18M8 6.5h.01M11 6.5h.01m2 7.5 2 2 4-4" /></svg>;
  }
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><circle cx="12" cy="12" r="9" /><path d="M12 8v8m-4-4h8" /></svg>;
}

function CopyIcon() {
  return <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><rect x="8" y="8" width="12" height="13" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h2" /></svg>;
}

function PlatformIcon({ platform }: { platform: InstallPlatform }) {
  if (platform === "android") {
    return <svg viewBox="0 0 24 24" fill="#3DDC84" aria-hidden="true" focusable="false"><path d="m17.523 15.341 1.931-3.345a.399.399 0 0 0-.146-.546.399.399 0 0 0-.546.146l-1.956 3.388a11.898 11.898 0 0 0-4.806-.994c-1.696 0-3.322.353-4.806.994l-1.956-3.388a.399.399 0 0 0-.546-.146.399.399 0 0 0-.146.546l1.931 3.345C2.99 17.113.638 20.408.294 24h23.412c-.344-3.592-2.696-6.887-6.183-8.659zM6.622 20.539a.978.978 0 1 1 0-1.956.978.978 0 0 1 0 1.956zm10.756 0a.978.978 0 1 1 0-1.956.978.978 0 0 1 0 1.956z" transform="translate(0 -6)" /></svg>;
  }
  return <svg viewBox="0 0 24 24" fill="#fff" aria-hidden="true" focusable="false"><path d="M17.05 12.54c.03 3.28 2.88 4.37 2.91 4.39-.02.08-.46 1.56-1.51 3.09-.91 1.32-1.85 2.64-3.34 2.67-1.46.03-1.93-.86-3.6-.86-1.67 0-2.19.83-3.57.89-1.44.05-2.54-1.44-3.46-2.76-1.88-2.71-3.31-7.65-1.38-10.99.96-1.66 2.67-2.71 4.53-2.74 1.41-.03 2.75.95 3.6.95.84 0 2.43-1.18 4.09-1.01.7.03 2.67.28 3.94 2.14-.1.06-2.35 1.37-2.21 4.23zM14.3 4.37c.76-.92 1.27-2.19 1.13-3.46-1.09.04-2.4.73-3.18 1.65-.7.81-1.31 2.1-1.14 3.34 1.21.09 2.44-.62 3.19-1.53z" /></svg>;
}
