import { useTranslation } from "react-i18next";

import type { AdminAiAgentName, AdminAiAgentRunnerCapability } from "./types";

const agentNames: AdminAiAgentName[] = ["antigravity", "codex", "claude"];

export type AgentServicePanelProps = {
  runners: AdminAiAgentRunnerCapability[];
  debugMode?: boolean;
  loading: boolean;
  unavailable: boolean;
  selectedAgent: AdminAiAgentName | null;
  selectedModelId: string | null;
  selectedModelLabel?: string | null;
  onSelectAgent: (agent: AdminAiAgentName) => void;
  onAuthenticate: (agent: AdminAiAgentName) => void;
  onReauthenticate: (agent: AdminAiAgentName) => void;
  onLogout: (agent: AdminAiAgentName) => void;
  onTest: () => void;
  testDisabled: boolean;
};

export function AgentServicePanel({
  runners,
  debugMode = false,
  loading,
  unavailable,
  selectedAgent,
  selectedModelId,
  selectedModelLabel,
  onSelectAgent,
  onAuthenticate,
  onReauthenticate,
  onLogout,
  onTest,
  testDisabled,
}: AgentServicePanelProps) {
  const { t, i18n } = useTranslation();
  const runnerByAgent = new Map(runners.map((runner) => [runner.agent, runner]));
  const selectedLabel = selectedAgent
    ? t(`admin.aiSettings.agents.${selectedAgent}`)
    : t("admin.aiSettings.agentService.none");
  const serviceLabel = loading
    ? t("admin.aiSettings.agentLoading")
    : unavailable
      ? t("admin.aiSettings.agentService.unavailable")
      : t("admin.aiSettings.agentService.online");

  return (
    <section className="admin-panel admin-agent-service" aria-labelledby="agent-service-title">
      <header className="admin-agent-service__header">
        <div>
          <p className="admin-kicker">{t("admin.aiSettings.agentService.eyebrow")}</p>
          <h2 id="agent-service-title">{t("admin.aiSettings.agentService.title")}</h2>
          <p>{t("admin.aiSettings.agentService.subtitle")}</p>
        </div>
        <span
          className={`admin-agent-service__status${unavailable ? " is-unavailable" : ""}`}
          role="status"
        >
          <strong>{t("admin.aiSettings.agentStatus")}</strong>
          <span>{serviceLabel}</span>
        </span>
      </header>

      <div className="admin-agent-service__cards">
        {agentNames.map((agent) => {
          const runner = runnerByAgent.get(agent) ?? unavailableRunner(agent);
          const label = t(`admin.aiSettings.agents.${agent}`);
          const mock = debugMode && agent === "claude" && runner.debug_status === "mock";
          const authSupported = !mock && runner.auth_mode === "browser_link";
          const authenticated = runner.auth_state === "authenticated" && authSupported;
          const authAction = mock ? "MOCK" : authenticated
            ? t("admin.aiSettings.agentService.reauthenticate")
            : t("admin.aiSettings.agentService.authenticate");
          return (
            <article
              className={`admin-agent-card${selectedAgent === agent ? " is-selected" : ""}`}
              key={agent}
              role="group"
              aria-label={label}
            >
              <button
                className="admin-agent-card__select"
                type="button"
                aria-pressed={selectedAgent === agent}
                aria-label={t("admin.aiSettings.agentService.selectAgent", { agent: label })}
                onClick={() => onSelectAgent(agent)}
              >
                <span>{t("admin.aiSettings.agentService.selectAgent", { agent: label })}</span>
                <strong>{label}</strong>
              </button>
              {debugMode && <p role="status">{debugStatusLabel(runner.debug_status, i18n.resolvedLanguage === "en")}</p>}
              <dl className="admin-agent-card__details">
                <div>
                  <dt>{t("admin.aiSettings.agentService.installation")}</dt>
                  <dd>{mock ? (i18n.resolvedLanguage === "en" ? "Not required (MOCK)" : "لازم نیست (MOCK)") : runner.installed
                    ? t("admin.aiSettings.agentInstalled")
                    : t("admin.aiSettings.agentService.notInstalled")}</dd>
                </div>
                <div>
                  <dt>{t("admin.aiSettings.agentService.version")}</dt>
                  <dd>{mock ? "MOCK" : runner.version ?? t("admin.aiSettings.agentService.none")}</dd>
                </div>
                <div>
                  <dt>{t("admin.aiSettings.agentService.authentication")}</dt>
                  <dd>{mock ? "MOCK" : t(`admin.aiSettings.auth.${runner.auth_state}`)}</dd>
                </div>
                <div>
                  <dt>{t("admin.aiSettings.agentService.authenticationMethod")}</dt>
                  <dd>{t(`admin.aiSettings.authMode.${runner.auth_mode}`)}</dd>
                </div>
              </dl>
              <button
                className="admin-agent-card__auth"
                type="button"
                disabled={!runner.installed || !authSupported || loading || unavailable}
                onClick={() => (authenticated ? onReauthenticate(agent) : onAuthenticate(agent))}
                aria-label={`${authAction} ${label}`}
              >
                {authAction}
              </button>
              {authenticated && <button
                className="admin-agent-card__logout"
                type="button"
                disabled={loading || unavailable}
                onClick={() => onLogout(agent)}
                aria-label={`${t("admin.aiSettings.agentService.logout")} ${label}`}
              >
                {t("admin.aiSettings.agentService.logout")}
              </button>}
              {runner.installed && !authSupported && !mock && <p className="admin-agent-card__auth-note" role="note">
                {t("admin.aiSettings.agentService.browserAuthUnavailable")}
              </p>}
            </article>
          );
        })}
      </div>

      <div className="admin-agent-service__selection">
        <label className="admin-agent-service__agent-select" htmlFor="agent-service-agent">
          <span>{t("admin.aiSettings.agent")}</span>
          <select
            id="agent-service-agent"
            value={selectedAgent ?? ""}
            onChange={(event) => onSelectAgent(event.target.value as AdminAiAgentName)}
          >
            {agentNames.map((agent) => (
              <option key={agent} value={agent}>{t(`admin.aiSettings.agents.${agent}`)}</option>
            ))}
          </select>
        </label>
        <div className="admin-agent-service__selected-values">
          <span>{t("admin.aiSettings.agentService.selectedAgent")}: {selectedLabel}</span>
          <span>{t("admin.aiSettings.agentService.selectedModel")}: {selectedModelLabel ?? selectedModelId ?? t("admin.aiSettings.agentService.none")}</span>
        </div>
        <button
          type="button"
          aria-label={t("admin.aiSettings.testAgent")}
          onClick={onTest}
          disabled={testDisabled}
        >
          {t("admin.aiSettings.agentService.testSelected")}
        </button>
      </div>
    </section>
  );
}

function unavailableRunner(agent: AdminAiAgentName): AdminAiAgentRunnerCapability {
  return {
    agent,
    installed: false,
    version: null,
    auth_state: "unknown",
    auth_mode: "unknown",
    models: [],
  };
}

function debugStatusLabel(status: AdminAiAgentRunnerCapability["debug_status"], english: boolean) {
  const labels: Record<string, [string, string]> = {
    mock: ["MOCK — no model or tools execute. No login is required.", "MOCK — هیچ مدل یا ابزاری اجرا نمی‌شود؛ ورود لازم نیست."],
    available: ["Debug profile available; test before enabling.", "پروفایل دیباگ در دسترس است؛ پیش از فعال‌سازی تست کنید."],
    not_installed: ["CLI is not installed.", "CLI نصب نشده است."],
    authentication_required: ["Agent login is required in Agent Service.", "ورود ایجنت در Agent Service لازم است."],
    models_unavailable: ["No model was discovered or explicitly configured in the CLI.", "مدلی از CLI کشف یا صریحاً تنظیم نشده است."],
    native_tool_isolation_unavailable: ["This CLI version cannot safely restrict native tools for debugging.", "جداسازی امن ابزارهای داخلی برای دیباگ در این نسخهٔ CLI تأیید نشده است."],
    unknown: ["Debug capability is unverified.", "قابلیت دیباگ هنوز تأیید نشده است."],
  };
  return (labels[status ?? "unknown"] ?? labels.unknown)[english ? 0 : 1];
}
