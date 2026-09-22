import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";

import { LanguageSwitcher } from "../../shared/LanguageSwitcher";
import { BrandLogo } from "../../shared/BrandLogo";

export function PublicPageFrame({ children }: { children: ReactNode }) {
  const { i18n, t } = useTranslation();
  const english = i18n.resolvedLanguage === "en";
  const l = (fa: string, en: string) => english ? en : fa;

  return (
    <main className="public-account-page fitician-page" dir={english ? "ltr" : "rtl"}>
      <div className="public-account-page__container">
        <header className="public-account-page__header">
          <Link className="fitician-brand-link public-account-page__brand" to="/" aria-label={t("common.brand")}>
            <BrandLogo testId="public-account-brand-logo" />
          </Link>
          <LanguageSwitcher />
        </header>
        {children}
        <footer className="public-account-page__footer">
          <Link to="/delete-account">{l("حذف حساب", "Delete account")}</Link>
          <Link to="/privacy">{l("سیاست حریم خصوصی", "Privacy policy")}</Link>
        </footer>
      </div>
    </main>
  );
}
