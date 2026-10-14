import { GoogleSignInFlowError } from "./googleCredential";

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

const GOOGLE_NATIVE_TIMEOUT_MS = 90_000;
const GOOGLE_TIMEOUT_MESSAGE = "زمان انتظار ورود گوگل تمام شد. پنجره گوگل را ببندید و دوباره تلاش کنید یا با ایمیل وارد شوید.";
const pendingNativeOperations = new WeakSet<AndroidGoogleSignInApi>();

function tokenFromResponse(response: AndroidGoogleSignInResponse): string | null {
  if (response.type !== "success") return null;
  const rawToken = response.data?.idToken;
  if (typeof rawToken !== "string") return null;
  const token = rawToken.trim();
  return token || null;
}

export async function requestAndroidGoogleIdToken(
  api: AndroidGoogleSignInApi,
  webClientId: string | null,
): Promise<string> {
  const audience = webClientId?.trim();
  if (!audience) {
    throw new GoogleSignInFlowError("ورود با گوگل در این محیط پیکربندی نشده است.");
  }

  if (pendingNativeOperations.has(api)) {
    throw new GoogleSignInFlowError("ورود قبلی گوگل هنوز پاسخ نداده است. پنجره گوگل را ببندید یا با ایمیل وارد شوید.");
  }
  pendingNativeOperations.add(api);
  let expired = false;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const assertActive = () => {
    if (expired) throw new GoogleSignInFlowError(GOOGLE_TIMEOUT_MESSAGE);
  };

  const operation = async () => {
    try {
      api.configure({ webClientId: audience });
      await api.checkPlayServices();
      assertActive();
      let response = await api.signIn();
      assertActive();
      if (response.type === "noSavedCredentialFound") {
        response = await api.createAccount();
        assertActive();
      }
      if (response.type === "noSavedCredentialFound") {
        response = await api.presentExplicitSignIn();
        assertActive();
      }
      if (response.type === "cancelled") {
        throw new GoogleSignInFlowError("ورود با گوگل لغو شد.");
      }

      const idToken = tokenFromResponse(response);
      if (!idToken) {
        throw new GoogleSignInFlowError("ورود با گوگل انجام نشد. دوباره تلاش کنید.");
      }
      return idToken;
    } finally {
      // The native API cannot cancel a pending sheet. Keep retries from opening
      // competing sheets until the original native operation actually settles.
      pendingNativeOperations.delete(api);
    }
  };
  const deadline = new Promise<never>((_resolve, reject) => {
    timer = setTimeout(() => {
      expired = true;
      reject(new GoogleSignInFlowError(GOOGLE_TIMEOUT_MESSAGE));
    }, GOOGLE_NATIVE_TIMEOUT_MS);
  });
  try {
    return await Promise.race([operation(), deadline]);
  } finally {
    if (timer !== undefined) clearTimeout(timer);
  }
}
