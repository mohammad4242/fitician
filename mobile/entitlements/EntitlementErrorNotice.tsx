import {
  resolveAppError,
} from "@fitician/core";

import { Notice } from "../ui/components";
import { useMobileEntitlements } from "./EntitlementProvider";

export function EntitlementErrorNotice() {
  const { error, retry } = useMobileEntitlements();
  if (error === null) return null;

  const resolved = resolveAppError(error, {
    audience: "member",
    context: "access",
    locale: "fa",
  });
  if (resolved.severity === "silent") return null;
  const retryable = resolved.retryable;

  return (
    <Notice
      actionLabel={retryable ? (resolved.action ?? "تلاش دوباره") : undefined}
      message={resolved.message}
      onAction={retryable ? retry : undefined}
      technicalDetails={resolved}
      title={resolved.title}
      variant={resolved.severity === "warning" ? "warning" : "danger"}
    />
  );
}
