export interface GoogleAuthResultLike {
  readonly errorCode?: string | null;
  readonly params?: Readonly<Record<string, string>>;
  readonly type: string;
}

export class GoogleSignInFlowError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "GoogleSignInFlowError";
  }
}

export function googleCredentialFromResult(result: GoogleAuthResultLike): string | null {
  if (result.type !== "success") {
    return null;
  }
  const credential = result.params?.id_token?.trim();
  return credential === "" || credential === undefined ? null : credential;
}

export function googleResultMessage(result: GoogleAuthResultLike): string {
  return result.type === "cancel"
    ? "ورود با گوگل لغو شد."
    : "ورود با گوگل انجام نشد. دوباره تلاش کنید.";
}

export const GOOGLE_SIGN_IN_TIMEOUT_MS = 45_000;
export const GOOGLE_TIMEOUT_MESSAGE = "مهلت ورود با گوگل تمام شد. پنجره گوگل را ببندید و دوباره تلاش کنید یا با ایمیل وارد شوید.";

// Racing does not cancel native work. Callers must discard late results.
export async function withGoogleSignInTimeout<T>(
  operation: () => Promise<T>,
  timeoutMs = GOOGLE_SIGN_IN_TIMEOUT_MS,
): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  try {
    return await Promise.race([
      Promise.resolve().then(operation),
      new Promise<never>((_resolve, reject) => {
        timer = setTimeout(() => reject(new GoogleSignInFlowError(GOOGLE_TIMEOUT_MESSAGE)), timeoutMs);
      }),
    ]);
  } finally {
    clearTimeout(timer);
  }
}
