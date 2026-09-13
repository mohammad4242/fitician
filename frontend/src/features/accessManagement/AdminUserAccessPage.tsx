import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";

import {
  searchAccessUsers,
  type AdminMemberSummary,
} from "./adminAccessApi";

export function AdminUserAccessPage() {
  const { i18n, t } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get("q") ?? "";
  const [input, setInput] = useState(query);
  const [users, setUsers] = useState<AdminMemberSummary[]>([]);
  const [state, setState] = useState<"loading" | "ready" | "error">("loading");
  const english = i18n.resolvedLanguage === "en";

  useEffect(() => {
    setInput(query);
    let active = true;
    setState("loading");
    void searchAccessUsers(query === "" ? {} : { q: query })
      .then((result) => {
        if (!active) return;
        setUsers(result);
        setState("ready");
      })
      .catch(() => {
        if (active) setState("error");
      });
    return () => { active = false; };
  }, [query]);

  function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const next = input.trim();
    setSearchParams(next === "" ? {} : { q: next });
  }

  return (
    <main className="access-admin-page fitsho-page">
      <div className="access-admin-page__container">
        <header className="access-admin-page__header">
          <div>
            <p className="eyebrow eyebrow--accent">{t("adminAccess.user")}</p>
            <h1>{t("adminAccess.usersAccess")}</h1>
            <p>{t("adminAccess.usersDescription", "دسترسی و سابقه هر عضو را از یک نقطه بررسی کنید.")}</p>
          </div>
        </header>

        <form className="access-admin-search" onSubmit={submit} role="search">
          <label>
            {t("adminAccess.searchUsers")}
            <input
              aria-label={t("adminAccess.searchUsers")}
              onChange={(event) => setInput(event.currentTarget.value)}
              placeholder={t("adminAccess.searchPlaceholder")}
              type="search"
              value={input}
            />
          </label>
          <button className="access-admin-button access-admin-button--primary" type="submit">{t("adminAccess.search")}</button>
        </form>

        {state === "loading" && <p className="access-admin-status" role="status">{t("adminAccess.loading")}</p>}
        {state === "error" && <p className="access-admin-status access-admin-status--error" role="alert">{t("adminAccess.loadError")}</p>}
        {state === "ready" && users.length === 0 && <p className="access-admin-status">{t("adminAccess.noUsers")}</p>}
        {state === "ready" && users.length > 0 && (
          <div className="access-user-list">
            {users.map((user) => (
              <article className="access-user-card" data-testid={`access-user-${user.user_id}`} key={user.user_id}>
                <div className="access-user-card__identity">
                  <span className="access-admin-code">{user.user_id}</span>
                  <h2>{user.display_name ?? user.email ?? user.phone_number ?? user.user_id}</h2>
                  <p>{user.email ?? user.phone_number ?? "—"}</p>
                </div>
                <dl className="access-user-card__facts">
                  <div><dt>{t("adminAccess.signupDate")}</dt><dd>{formatDate(user.created_at, english)}</dd></div>
                  <div><dt>{t("adminAccess.currentPackage")}</dt><dd>{t(`entitlements.packageLabels.${user.primary_package}`, { defaultValue: user.primary_package })}</dd></div>
                  <div><dt>{t("adminAccess.trialState")}</dt><dd>{user.trial_active ? t("entitlements.trialActive") : t("adminAccess.inactive")}</dd></div>
                  <div><dt>{t("adminAccess.accessEnd")}</dt><dd>{user.paid_access_end === null ? "—" : formatDate(user.paid_access_end, english)}</dd></div>
                </dl>
                <Link className="access-admin-button access-admin-button--quiet" to={`/admin/billing/users/${user.user_id}`}>
                  {t("adminAccess.viewAccess", "مشاهده دسترسی")}
                </Link>
              </article>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}

function formatDate(value: string, english: boolean): string {
  return new Intl.DateTimeFormat(english ? "en" : "fa-IR", { dateStyle: "medium" }).format(new Date(value));
}
