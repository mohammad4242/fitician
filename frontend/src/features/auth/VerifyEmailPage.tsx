import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import { AuthShell } from "../../shared/AuthShell";
import { AppErrorNotice } from "../../shared/AppErrorNotice";
import * as api from "./api";
import { normalizeAuthError } from "./authError";

type VerificationState = "checking" | "verified" | "invalid";

export function VerifyEmailPage() {
  const { t, i18n } = useTranslation();
  const locale = i18n.resolvedLanguage === "en" ? "en" : "fa";
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [state, setState] = useState<VerificationState>("checking");
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    let active = true;
    if (!token) {
      setState("invalid");
      return () => {
        active = false;
      };
    }

    void api
      .verifyEmail(token)
      .then(() => {
        if (active) setState("verified");
      })
      .catch((requestError: unknown) => {
        if (active) {
          setError(normalizeAuthError(requestError, "verification"));
          setState("invalid");
        }
      });

    return () => {
      active = false;
    };
  }, [token]);

  return (
    <AuthShell>
      <div className="form-heading">
        <p className="eyebrow eyebrow--accent">{t("emailVerification.eyebrow")}</p>
        <h2 className="fitician-display">{t("emailVerification.title")}</h2>
        <p>{t("emailVerification.subtitle")}</p>
      </div>

      {state === "checking" && (
        <p className="form-success" role="status" aria-live="polite">
          {t("emailVerification.checking")}
        </p>
      )}
      {state === "verified" && (
        <p className="form-success" role="status" aria-live="polite">
          {t("emailVerification.success")}
        </p>
      )}
      {state === "invalid" && (
        error === null ? (
          <p className="form-error" role="alert" aria-live="polite">
            {t("emailVerification.invalidToken")}
          </p>
        ) : (
          <AppErrorNotice audience="member" context="auth" error={error} locale={locale} />
        )
      )}

      <p className="form-alternative">
        <Link to="/login">{t("emailVerification.backToLogin")}</Link>
      </p>
    </AuthShell>
  );
}
