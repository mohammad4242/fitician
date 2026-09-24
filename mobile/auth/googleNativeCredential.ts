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

  api.configure({ webClientId: audience });
  await api.checkPlayServices();

  let response = await api.signIn();
  if (response.type === "noSavedCredentialFound") {
    response = await api.createAccount();
  }
  if (response.type === "noSavedCredentialFound") {
    response = await api.presentExplicitSignIn();
  }
  if (response.type === "cancelled") {
    throw new GoogleSignInFlowError("ورود با گوگل لغو شد.");
  }

  const idToken = tokenFromResponse(response);
  if (!idToken) {
    throw new GoogleSignInFlowError("ورود با گوگل انجام نشد. دوباره تلاش کنید.");
  }
  return idToken;
}
