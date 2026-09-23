import * as WebBrowser from "expo-web-browser";
import { useIdTokenAuthRequest } from "expo-auth-session/providers/google";
import { useCallback } from "react";
import { Platform } from "react-native";

import { getMobileRuntimeConfig } from "../config/nativeRuntimeConfig";
import { googleClientIdForPlatform } from "../config/runtimeConfig";
import { googleCredentialFromResult, googleResultMessage, GoogleSignInFlowError } from "./googleCredential";

WebBrowser.maybeCompleteAuthSession();

export interface GoogleSignInController {
  readonly available: boolean;
  readonly ready: boolean;
  readonly signIn: () => Promise<string>;
}

export function useGoogleSignIn(): GoogleSignInController {
  const runtime = getMobileRuntimeConfig();
  const clientId = googleClientIdForPlatform(Platform.OS, runtime);
  const available = clientId !== null;
  const clientConfig = Platform.OS === "ios"
    ? { iosClientId: clientId ?? "" }
    : Platform.OS === "android"
      ? { androidClientId: clientId ?? "" }
      : { webClientId: clientId ?? "" };
  const [request, , promptAsync] = useIdTokenAuthRequest(
    {
      ...clientConfig,
      selectAccount: true,
    },
    { scheme: "fitician" },
  );

  const signIn = useCallback(async () => {
    if (!available) {
      throw new GoogleSignInFlowError("ورود با گوگل در این محیط پیکربندی نشده است.");
    }
    const result = await promptAsync();
    const credential = googleCredentialFromResult(result);
    if (credential === null) {
      throw new GoogleSignInFlowError(googleResultMessage(result));
    }
    return credential;
  }, [available, promptAsync]);

  return { available, ready: request !== null, signIn };
}
