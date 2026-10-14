import { ApiError, resolveAppError } from "@fitician/core";

export function agentNetworkMessage(
  code: string | null | undefined,
  provider: string | null | undefined,
  context: "body_analysis" | "nutrition",
): string | null {
  if (code === "agent_network_unavailable") {
    return resolveAppError(new ApiError(503, "", null, code, { retryable: true }), {
      audience: "member", context, locale: "fa",
    }).message;
  }
  // Older servers persist generic transport errors. Identify the Agent provider
  // without asserting which network, upstream service or DNS caused the error.
  // Food-photo responses omit the provider. Keep their connection-error copy
  // generic; body results expose it and retain other providers' existing copy.
  if (code === "connection_failure"
    && (context === "nutrition" || provider?.startsWith("agent_service:"))) {
    return "ارتباط با سرویس هوشمند برقرار نشد. کمی بعد دوباره تلاش کنید.";
  }
  return null;
}
