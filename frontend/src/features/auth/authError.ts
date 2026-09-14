import type { TFunction } from "i18next";

import type { ErrorLocale } from "@fitician/core";

import { webErrorMessage } from "../../shared/appError";

export function authErrorMessage(error: unknown, t: TFunction, locale: ErrorLocale = "fa"): string {
  return webErrorMessage(error, t("errors.generic"), {
    audience: "member",
    context: "auth",
    locale,
  });
}
