import { useEffect, useState, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { BrandLogo } from "../../shared/BrandLogo";
import { LanguageSwitcher } from "../../shared/LanguageSwitcher";
import { usePwaInstall } from "../../pwa/usePwaInstall";
import { detectInstallEnvironment } from "./installEnvironment";
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
  appIconAlt: string;
  appIconCaption: string;
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
  chromiumUnavailableTitle: string;
  chromiumUnavailableDescription: string;
  desktopTitle: string;
  desktopDescription: string;
  continueAction: string;
}> = {
  fa: {
    eyebrow: "بدون نیاز به App Store",
    heroTitle: "فیتیشن را مثل یک اپ روی آیفونت نصب کن",
    installedTitle: "فیتیشن روی دستگاهت نصب شده",
    heroDescription: "فقط چند لمس تا فیتیشن روی صفحهٔ اصلی آیفونت؛ همیشه دم دست.",
    installedDescription: "فیتیشن آماده است؛ از آیکن روی صفحهٔ اصلی بازش کن.",
    appIconAlt: "آیکن فیتیشن",
    appIconCaption: "روی صفحهٔ اصلی",
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
    chromiumUnavailableTitle: "فیتیشن همیشه در دسترس توست",
    chromiumUnavailableDescription: "در حال حاضر مرورگر گزینهٔ نصب را آماده نکرده. می‌توانی فیتیشن را همین‌جا در مرورگر استفاده کنی.",
    desktopTitle: "این صفحه برای نصب روی موبایل طراحی شده",
    desktopDescription: "فیتیشن را روی موبایلت باز کن تا آن را به صفحهٔ اصلی اضافه کنی. در همین دستگاه هم می‌توانی نسخهٔ وب را ببینی.",
    continueAction: "ورود به فیتیشن",
  },
  en: {
    eyebrow: "No App Store needed",
    heroTitle: "Add Fitician to your iPhone Home Screen",
    installedTitle: "Fitician is installed on this device",
    heroDescription: "A few taps put Fitician on your iPhone Home Screen, ready whenever you need it.",
    installedDescription: "Fitician is ready. Open it from the icon on your Home Screen.",
    appIconAlt: "Fitician app icon",
    appIconCaption: "On your Home Screen",
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
    chromiumUnavailableTitle: "Keep Fitician close at hand",
    chromiumUnavailableDescription: "Your browser has not made its install option available yet. You can keep using Fitician here in the browser.",
    desktopTitle: "Install Fitician on your phone",
    desktopDescription: "Open Fitician on your phone to add it to the Home Screen. You can also continue to the web app on this device.",
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
  const navigatorWithStandalone = navigator as Navigator & { standalone?: boolean };
  const environment = detectInstallEnvironment({
    userAgent: navigator.userAgent,
    platform: navigator.platform,
    maxTouchPoints: navigator.maxTouchPoints,
    standalone: navigatorWithStandalone.standalone === true,
    displayModeStandalone: window.matchMedia?.("(display-mode: standalone)").matches === true,
    canPrompt,
    pwaState,
  });

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
            <div className="public-install__icon-stage">
              <span className="public-install__icon-caption">{copy.appIconCaption}</span>
              <div className="public-install__icon-frame">
                <img
                  src="/pwa/apple-touch-icon.png"
                  alt={copy.appIconAlt}
                  width="180"
                  height="180"
                  fetchPriority="high"
                  data-testid="public-install-app-icon"
                />
              </div>
            </div>
          </section>

          <div className="public-install__content">
            {environment === "ios-in-app-browser" && (
              <section className="public-install__panel public-install__panel--handoff" aria-labelledby="public-install-handoff-title">
                <div className="public-install__panel-heading">
                  <span className="public-install__panel-mark" aria-hidden="true"><StepIcon name="share" /></span>
                  <div>
                    <p className="public-install__section-kicker">{language === "fa" ? "اول مرورگر اصلی" : "FIRST, YOUR MAIN BROWSER"}</p>
                    <h2 id="public-install-handoff-title">{copy.instagramTitle}</h2>
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

            {(environment === "ios" || environment === "ios-in-app-browser") && (
              <section className="public-install__panel public-install__panel--steps" aria-labelledby="public-install-steps-title">
                <div className="public-install__panel-heading">
                  <span className="public-install__panel-mark public-install__panel-mark--steps" aria-hidden="true">4</span>
                  <div>
                    <p className="public-install__section-kicker">{language === "fa" ? "نصب از Safari" : "FROM SAFARI"}</p>
                    <h2 id="public-install-steps-title">{copy.iosTitle}</h2>
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
                  <Link className="public-install__button" to="/">{copy.continueAction}</Link>
                </div>
              </section>
            )}

            {environment === "chromium-prompt" && (
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

            {environment === "chromium-unavailable" && (
              <section className="public-install__panel public-install__panel--state" aria-labelledby="public-install-state-title">
                <span className="public-install__panel-mark" aria-hidden="true"><StepIcon name="home" /></span>
                <div>
                  <p className="public-install__section-kicker">{language === "fa" ? "نسخهٔ وب" : "WEB APP"}</p>
                  <h2 id="public-install-state-title">{copy.chromiumUnavailableTitle}</h2>
                  <p className="public-install__panel-description">{copy.chromiumUnavailableDescription}</p>
                  <Link className="public-install__button public-install__button--quiet" to="/">{copy.continueAction}</Link>
                </div>
              </section>
            )}

            {environment === "other" && (
              <section className="public-install__panel public-install__panel--state" aria-labelledby="public-install-state-title">
                <span className="public-install__panel-mark" aria-hidden="true"><StepIcon name="home" /></span>
                <div>
                  <p className="public-install__section-kicker">{language === "fa" ? "فیتیشن روی موبایل" : "FITICIAN ON MOBILE"}</p>
                  <h2 id="public-install-state-title">{copy.desktopTitle}</h2>
                  <p className="public-install__panel-description">{copy.desktopDescription}</p>
                  <Link className="public-install__button public-install__button--quiet" to="/">{copy.continueAction}</Link>
                </div>
              </section>
            )}
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
