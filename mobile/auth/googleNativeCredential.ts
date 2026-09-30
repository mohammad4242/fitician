import { GOOGLE_TIMEOUT_MESSAGE, GoogleSignInFlowError, withGoogleSignInTimeout } from "./googleCredential";

export interface AndroidGoogleSignInResponse {
  readonly data: { readonly idToken?: unknown } | null;
  readonly type: string;
}

export interface AndroidGoogleSignInApi {
  readonly checkPlayServices: () => Promise<void>;
  readonly configure: (config: { readonly webClientId: string }) => void;
  readonly createAccount: () => Promise<AndroidGoogleSignInResponse>;
  readonly presentExplicitSignIn: () => Promise<AndroidGoogleSignInResponse>;
  readonly signIn: () => Promise<AndroidGoogleSignInResponse>;
}

function tokenFromResponse(response: AndroidGoogleSignInResponse): string | null {
  if (response.type !== "success") return null;
  const rawToken = response.data?.idToken;
  if (typeof rawToken !== "string") return null;
  const token = rawToken.trim();
  return token || null;
}

// The SDK has no cancellation API. Do not open a second native sheet while
// a timed-out request is still pending, or let its result advance the flow.
const pendingApis = new WeakSet<AndroidGoogleSignInApi>();

function safeNativeError(error: unknown): GoogleSignInFlowError {
  if (error instanceof GoogleSignInFlowError) return error;
  const code = typeof error === "object" && error !== null && "code" in error ? String(error.code) : "";
  const message = error instanceof Error ? error.message : "";
  const detail = `${code} ${message}`;
  if (/DEVELOPER_ERROR|\b10\b|developer console|not configured|configure\(\)|SHA-?1|client.?id/iu.test(detail)) {
    return new GoogleSignInFlowError("پیکربندی ورود با گوگل صحیح نیست. لطفاً با ایمیل وارد شوید.");
  }
  if (/PLAY_SERVICES|play services/iu.test(detail)) {
    return new GoogleSignInFlowError("سرویس‌های گوگل در دسترس نیستند. آن‌ها را به‌روزرسانی کنید یا با ایمیل وارد شوید.");
  }
  if (/cancel/iu.test(detail)) return new GoogleSignInFlowError("ورود با گوگل لغو شد.");
  if (/network|connection|offline/iu.test(detail)) {
    return new GoogleSignInFlowError("اتصال به گوگل برقرار نشد. اتصال اینترنت را بررسی کنید یا با ایمیل وارد شوید.");
  }
  return new GoogleSignInFlowError("ورود با گوگل انجام نشد. دوباره تلاش کنید یا با ایمیل وارد شوید.");
}

export async function requestAndroidGoogleIdToken(
  api: AndroidGoogleSignInApi,
  webClientId: string | null,
): Promise<string> {
  const audience = webClientId?.trim();
  if (!audience) {
    throw new GoogleSignInFlowError("ورود با گوگل در این محیط پیکربندی نشده است.");
  }
  if (pendingApis.has(api)) {
    throw new GoogleSignInFlowError("درخواست قبلی گوگل هنوز باز است. پنجره گوگل را ببندید یا با ایمیل وارد شوید.");
  }
  pendingApis.add(api);
  let active = true;
  const ensureActive = () => {
    if (!active) throw new GoogleSignInFlowError(GOOGLE_TIMEOUT_MESSAGE);
  };
  const operation = (async () => {
    api.configure({ webClientId: audience });
    await api.checkPlayServices();
    ensureActive();
    let response = await api.signIn();
    ensureActive();
    if (response.type === "noSavedCredentialFound") {
      response = await api.createAccount();
      ensureActive();
    }
    if (response.type === "noSavedCredentialFound") {
      response = await api.presentExplicitSignIn();
      ensureActive();
    }
    if (response.type === "cancelled") throw new GoogleSignInFlowError("ورود با گوگل لغو شد.");
    const idToken = tokenFromResponse(response);
    if (!idToken) throw new GoogleSignInFlowError("ورود با گوگل انجام نشد. دوباره تلاش کنید.");
    return idToken;
  })();
  void operation.then(() => pendingApis.delete(api), () => pendingApis.delete(api));
  try {
    return await withGoogleSignInTimeout(() => operation);
  } catch (error) {
    throw safeNativeError(error);
  } finally {
    active = false;
  }
}
