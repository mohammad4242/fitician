import { afterEach, expect, it, vi } from "vitest";

afterEach(() => vi.useRealTimers());

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

it.each(["checkPlayServices", "signIn", "createAccount", "presentExplicitSignIn"] as const)(
  "recovers when native %s never settles", async (stage) => {
    vi.useFakeTimers();
    const api = createApi();
    api.signIn.mockResolvedValue(noSavedCredential());
    api.createAccount.mockResolvedValue(noSavedCredential());
    api[stage].mockImplementation(() => new Promise(() => undefined));
    let outcome = "pending";
    const completed = requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")
      .catch((error: Error) => { outcome = error.message; });
    await vi.advanceTimersByTimeAsync(90_000);
    expect(outcome).toContain("زمان");
    await completed;
    expect(vi.getTimerCount()).toBe(0);
  },
);

it("does not open a fallback sheet after a timed-out native result arrives", async () => {
  vi.useFakeTimers();
  const api = createApi();
  let resolve!: (response: AndroidGoogleSignInResponse) => void;
  api.signIn.mockImplementation(() => new Promise((done) => { resolve = done; }));
  const completed = requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com").catch(() => undefined);
  await vi.advanceTimersByTimeAsync(90_000);
  resolve(noSavedCredential());
  await vi.advanceTimersByTimeAsync(0);
  expect(api.createAccount).not.toHaveBeenCalled();
  expect(api.presentExplicitSignIn).not.toHaveBeenCalled();
  await completed;
});

it("blocks a competing native retry until the original cancellation settles", async () => {
  vi.useFakeTimers();
  const api = createApi();
  let resolve!: (response: AndroidGoogleSignInResponse) => void;
  api.signIn.mockImplementation(() => new Promise((done) => { resolve = done; }));
  const completed = requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com").catch(() => undefined);
  await vi.advanceTimersByTimeAsync(90_000);
  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).rejects.toThrow("ورود قبلی");
  expect(api.configure).toHaveBeenCalledOnce();
  resolve({ data: null, type: "cancelled" });
  await vi.advanceTimersByTimeAsync(0);
  await completed;
  api.signIn.mockResolvedValue(success("test-retry-token"));
  await expect(requestAndroidGoogleIdToken(api, "web.apps.googleusercontent.com")).resolves.toBe("test-retry-token");
  expect(vi.getTimerCount()).toBe(0);
});
