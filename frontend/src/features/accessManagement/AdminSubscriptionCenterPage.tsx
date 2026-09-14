import { useTranslation } from "react-i18next";
import { Link, NavLink, Outlet } from "react-router-dom";

import "./accessManagement.css";

const sections = [
  { key: "plansPricing", path: "/admin/billing/offers" },
  { key: "campaignsTrials", path: "/admin/billing/campaigns" },
  { key: "usersAccess", path: "/admin/billing/users" },
  { key: "ordersPayments", path: "/admin/billing/orders" },
  { key: "changeHistory", path: "/admin/billing/audit" },
] as const;

export function AdminSubscriptionCenterPage() {
  const { t } = useTranslation();

  return (
    <div className="admin-subscription-center fitician-page">
      <div className="admin-subscription-center__container">
        <Link className="admin-subscription-center__back-link" to="/dashboard">
          <span aria-hidden="true">←</span>
          {t("onboarding.actions.back")}
        </Link>

        <header className="admin-subscription-center__hero">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.controlPlane")}</p>
            <h1>{t("adminAccess.title")}</h1>
            <p>{t("adminAccess.subtitle")}</p>
          </div>
          <span className="admin-subscription-center__signal" aria-hidden="true" />
        </header>

        <nav
          aria-label={t("adminAccess.title")}
          className="admin-subscription-center__nav"
        >
          {sections.map((section, index) => (
            <NavLink
              className={({ isActive }) => isActive ? "is-active" : undefined}
              key={section.path}
              to={section.path}
            >
              <span aria-hidden="true">{String(index + 1).padStart(2, "0")}</span>
              {t(`adminAccess.${section.key}`)}
            </NavLink>
          ))}
        </nav>

        <div className="admin-subscription-center__content">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
