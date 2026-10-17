import { createCorrelationId } from "./transport";

/** Keep at most two ambiguous requests in memory; the server scopes keys by member. */
export function createGenerationRequestKeys(uuid: () => string = createCorrelationId) {
  const pending = new Map<string, string>();
  function eligible(path: string, method?: string): boolean {
    return method === "POST" && (path === "/api/v1/workout-plans/generate"
      || path === "/api/v1/nutrition/plans");
  }
  return {
    headers(path: string, method: string | undefined, supplied: Headers): Headers {
      if (!eligible(path, method) || supplied.has("Idempotency-Key")) return supplied;
      const key = pending.get(path) ?? uuid();
      pending.set(path, key);
      const result = new Headers(supplied);
      result.set("Idempotency-Key", key);
      return result;
    },
    completed(path: string, status: number, key?: string | null): void {
      // Network failures, timeouts, 5xx, and rate limits
      // retain the key. A definitive response permits a fresh user action.
      if (status < 500 && status !== 408 && status !== 429
        && (key === undefined || key === pending.get(path))) pending.delete(path);
    },
    clear(): void { pending.clear(); },
  };
}
