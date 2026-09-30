import { expect, it, vi } from "vitest";

import { googleCredentialFromResult, googleResultMessage, withGoogleSignInTimeout } from "./googleCredential";

it("extracts only a non-empty Google ID token from a successful native result", () => {
  expect(
    googleCredentialFromResult({ params: { id_token: "signed-id-token" }, type: "success" }),
  ).toBe("signed-id-token");
  expect(googleCredentialFromResult({ params: {}, type: "success" })).toBeNull();
  expect(googleCredentialFromResult({ type: "cancel" })).toBeNull();
});

it.each(["success", "cancel"])("rejects late %s when Android suspends timers", async (outcome) => {
  vi.useFakeTimers();
  try {
    vi.setSystemTime(0);
    let resolve!: (value: string) => void;
    let reject!: (error: Error) => void;
    const result = withGoogleSignInTimeout(() => new Promise<string>((res, rej) => {
      resolve = res;
      reject = rej;
    }));
    await Promise.resolve();
    // Move wall time without executing the timer, as happens behind a native activity.
    vi.setSystemTime(46_000);
    if (outcome === "success") resolve("late-token");
    else reject(new Error("cancelled"));
    await expect(result).rejects.toThrow("مهلت ورود با گوگل تمام شد");
    expect(vi.getTimerCount()).toBe(0);
  } finally { vi.useRealTimers(); }
});

it("maps cancelled and failed Google prompts to safe messages", () => {
  expect(googleResultMessage({ type: "cancel" })).toBe("ورود با گوگل لغو شد.");
  expect(googleResultMessage({ errorCode: "access_denied", type: "error" })).toBe(
    "ورود با گوگل انجام نشد. دوباره تلاش کنید.",
  );
});
