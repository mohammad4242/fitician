import { useTranslation } from "react-i18next";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { useAuth } from "./AuthContext";

export function ProtectedRoute() {
  const { t, i18n } = useTranslation();
  const { user, loading, startupError, retryStartup } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <main className="loading-screen" aria-live="polite">
        <span className="loading-mark" aria-hidden="true" />
        <p>{t("common.loading")}</p>
      </main>
    );
  }

  if (startupError) {
    return (
      <main className="loading-screen">
        <AppErrorNotice
          audience="member"
          context="auth"
          error={startupError}
          locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
        />
        <button className="retry-button" type="button" onClick={retryStartup}>
          {t("common.retry")}
        </button>
      </main>
    );
  }

  if (user === null) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  return <Outlet />;
}
