import { expect, it, vi } from "vitest";

import {
  requestAndroidGoogleIdToken,
  type AndroidGoogleSignInApi,
  type AndroidGoogleSignInResponse,
} from "./googleNativeCredential";

function success(idToken: string): AndroidGoogleSignInResponse {
  return { data: { idToken }, type: "success" };
}

function noSavedCredential(): AndroidGoogleSignInResponse {
  return { data: null, type: "noSavedCredentialFound" };
}

function createApi() {
  return {
    checkPlayServices: vi.fn().mockResolvedValue(undefined),
    configure: vi.fn(),
    createAccount: vi.fn<() => Promise<AndroidGoogleSignInResponse>>(),
    presentExplicitSignIn: vi.fn<() => Promise<AndroidGoogleSignInResponse>>(),
    signIn: vi.fn<() => Promise<AndroidGoogleSignInResponse>>(),
  } satisfies AndroidGoogleSignInApi;
}

it("uses the Web ID only as Credential Manager token audience and returns the ID token", async () => {
  const api = createApi();
  api.signIn.mockResolvedValue(success("signed-google-id-token"));

  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).resolves.toBe(
    "signed-google-id-token",
  );
  expect(api.configure).toHaveBeenCalledWith({ webClientId: "web.apps.googleusercontent.com" });
  expect(api.checkPlayServices).toHaveBeenCalledOnce();
  expect(api.createAccount).not.toHaveBeenCalled();
});

it("opens account creation when Credential Manager has no saved credential", async () => {
  const api = createApi();
  api.signIn.mockResolvedValue(noSavedCredential());
  api.createAccount.mockResolvedValue(success("new-account-id-token"));

  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).resolves.toBe(
    "new-account-id-token",
  );
  expect(api.createAccount).toHaveBeenCalledOnce();
  expect(api.presentExplicitSignIn).not.toHaveBeenCalled();
});

it("uses the explicit Google sign-in prompt after both account sheets report no account", async () => {
  const api = createApi();
  api.signIn.mockResolvedValue(noSavedCredential());
  api.createAccount.mockResolvedValue(noSavedCredential());
  api.presentExplicitSignIn.mockResolvedValue(success("explicit-account-id-token"));

  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).resolves.toBe(
    "explicit-account-id-token",
  );
  expect(api.presentExplicitSignIn).toHaveBeenCalledOnce();
});

it("maps a cancelled account sheet to a safe Persian message", async () => {
  const api = createApi();
  api.signIn.mockResolvedValue({ data: null, type: "cancelled" });

  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).rejects.toThrow(
    "ورود با گوگل لغو شد.",
  );
});

it("does not start native sign-in without the configured Web token audience", async () => {
  const api = createApi();

  await expect(requestAndroidGoogleIdToken(api, null)).rejects.toThrow(
    "ورود با گوگل در این محیط پیکربندی نشده است.",
  );
  expect(api.configure).not.toHaveBeenCalled();
  expect(api.signIn).not.toHaveBeenCalled();
});

it("rejects a success response that contains no ID token", async () => {
  const api = createApi();
  api.signIn.mockResolvedValue({ data: { idToken: " " }, type: "success" });

  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).rejects.toThrow(
    "ورود با گوگل انجام نشد. دوباره تلاش کنید.",
  );
});

for (const stage of ["checkPlayServices", "signIn", "createAccount", "presentExplicitSignIn"] as const) {
  it(`times out a pending ${stage} and ignores its late result`, async () => {
    vi.useFakeTimers();
    try {
      const api = createApi();
      api.signIn.mockResolvedValue(noSavedCredential());
      api.createAccount.mockResolvedValue(noSavedCredential());
      let settle!: (value: never) => void;
      api[stage].mockImplementation(() => new Promise((resolve) => { settle = resolve; }));
      const result = requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com");
      const assertion = expect(result).rejects.toThrow("مهلت ورود با گوگل تمام شد");
      await vi.advanceTimersByTimeAsync(45_000);
      await assertion;
      await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).rejects.toThrow("درخواست قبلی");
      settle(success("late-token") as never);
      await vi.runAllTimersAsync();
      if (stage === "checkPlayServices") expect(api.signIn).not.toHaveBeenCalled();
      expect(vi.getTimerCount()).toBe(0);
    } finally { vi.useRealTimers(); }
  });
}

it.each([
  ["PLAY_SERVICES_NOT_AVAILABLE", "سرویس‌های گوگل"],
  ["Google Play Services are not available (status=1).", "سرویس‌های گوگل"],
  ["DEVELOPER_ERROR", "پیکربندی"],
  ["[10] Developer console is not set up correctly", "پیکربندی"],
  ["SIGN_IN_CANCELLED", "لغو شد"],
  ["Network error", "اتصال"],
])("maps native failure %s without exposing native details", async (message, expected) => {
  const api = createApi();
  api.signIn.mockRejectedValue(new Error(message));
  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).rejects.toThrow(expected);
});

it("does not open fallback sheets after a wall-clock deadline with suspended timers", async () => {
  vi.useFakeTimers();
  try {
    vi.setSystemTime(0);
    const api = createApi();
    let settle!: (response: AndroidGoogleSignInResponse) => void;
    api.signIn.mockImplementation(() => new Promise((resolve) => { settle = resolve; }));
    const result = requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com");
    await Promise.resolve();
    vi.setSystemTime(46_000);
    settle(noSavedCredential());
    await expect(result).rejects.toThrow("مهلت ورود با گوگل تمام شد");
    expect(api.createAccount).not.toHaveBeenCalled();
    expect(api.presentExplicitSignIn).not.toHaveBeenCalled();
  } finally { vi.useRealTimers(); }
});
