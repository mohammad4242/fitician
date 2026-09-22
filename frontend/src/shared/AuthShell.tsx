import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";

import { LanguageSwitcher } from "./LanguageSwitcher";
import { BrandLogo } from "./BrandLogo";

type AuthShellProps = {
  children: ReactNode;
};

export function AuthShell({ children }: AuthShellProps) {
  const { t } = useTranslation();

  return (
    <main className="auth-shell fitician-page">
      <section className="form-panel">
        <div className="form-panel__mobile-nav">
          <a className="fitician-brand-link auth-shell__brand" href="/" aria-label={t("common.brand")}>
            <BrandLogo testId="auth-brand-logo" />
          </a>
          <LanguageSwitcher />
        </div>
        <div className="form-wrap">{children}</div>
      </section>
    </main>
  );
}
