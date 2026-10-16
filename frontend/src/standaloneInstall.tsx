import "@fontsource/lalezar";
import "@fontsource-variable/sora";
import "@fontsource-variable/vazirmatn";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import i18n from "i18next";
import { initReactI18next } from "react-i18next";

import "./index.css";
import cafeBazaarIcon from "./assets/branding/cafe-bazaar-official.png";
import myketIcon from "./assets/branding/myket-official.svg";
import { PublicInstallPage } from "./features/install/PublicInstallPage";
import "./features/install/publicInstall.css";
import { applyDesignSystem } from "./styles/designSystem";

void i18n.use(initReactI18next).init({
  resources: {
    fa: { translation: { common: { switchToEnglish: "English" } } },
    en: { translation: { common: { switchToPersian: "فارسی" } } },
  },
  lng: localStorage.getItem("fitician-language") === "en" ? "en" : "fa",
  fallbackLng: "fa",
  interpolation: { escapeValue: false },
});
function applyLanguage(language: string) {
  const normalized = language.startsWith("en") ? "en" : "fa";
  document.documentElement.lang = normalized;
  document.documentElement.dir = normalized === "fa" ? "rtl" : "ltr";
  localStorage.setItem("fitician-language", normalized);
}
applyLanguage(i18n.resolvedLanguage ?? "fa");
i18n.on("languageChanged", applyLanguage);
applyDesignSystem(document.documentElement);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <PublicInstallPage
        standaloneNotice={{ fa: "برای نصب و استفاده، فیلترشکنتو خاموش کن.", en: "Turn off your VPN to install and use Fitician." }}
        hideHeroDescription
        storeIcons={{ cafeBazaar: cafeBazaarIcon, myket: myketIcon }}
        continueHref="https://fitician.fit/"
        iosInstallHref="https://fitician.fit/install"
        copyHref="https://fitician.fit/install"
      />
    </BrowserRouter>
  </StrictMode>,
);
