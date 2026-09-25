import { getPwaInstallState, type PwaInstallState } from "../../pwa/usePwaInstall";

export type InstallEnvironment =
  | "installed"
  | "ios-in-app-browser"
  | "ios"
  | "chromium-prompt"
  | "chromium-unavailable"
  | "other";

export type InstallEnvironmentInput = {
  userAgent: string;
  platform?: string;
  maxTouchPoints?: number;
  standalone?: boolean;
  displayModeStandalone?: boolean;
  canPrompt?: boolean;
  pwaState?: PwaInstallState;
};

export function detectInstallEnvironment(input: InstallEnvironmentInput): InstallEnvironment {
  const pwaState = getPwaInstallState({
    userAgent: input.userAgent,
    platform: input.platform,
    maxTouchPoints: input.maxTouchPoints,
    standalone: input.standalone === true,
    displayModeStandalone: input.displayModeStandalone === true,
  });

  if (input.pwaState === "installed" || pwaState === "installed") return "installed";

  if (pwaState === "ios-instructions") {
    return /(?:Instagram|FBAN|FBAV)/i.test(input.userAgent)
      ? "ios-in-app-browser"
      : "ios";
  }

  if (pwaState === "chromium") {
    return input.canPrompt === true ? "chromium-prompt" : "chromium-unavailable";
  }

  return "other";
}
