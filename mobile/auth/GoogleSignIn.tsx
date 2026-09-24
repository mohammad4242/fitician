import * as WebBrowser from "expo-web-browser";
import { useIdTokenAuthRequest } from "expo-auth-session/providers/google";
import { useCallback } from "react";
import { Platform } from "react-native";
import { GoogleOneTapSignIn } from "react-native-nitro-google-signin";

import { getMobileRuntimeConfig } from "../config/nativeRuntimeConfig";
import { googleClientIdForPlatform } from "../config/runtimeConfig";
import { googleCredentialFromResult, googleResultMessage, GoogleSignInFlowError } from "./googleCredential";
import { requestAndroidGoogleIdToken } from "./googleNativeCredential";

WebBrowser.maybeCompleteAuthSession();

export interface GoogleSignInController {
  readonly available: boolean;
  readonly ready: boolean;
  readonly signIn: () => Promise<string>;
}

export function useGoogleSignIn(): GoogleSignInController {
  const runtime = getMobileRuntimeConfig();
  const clientId = googleClientIdForPlatform(Platform.OS, runtime);
  const available = Platform.OS === "android"
    ? clientId !== null && runtime.googleWebClientId !== null
    : clientId !== null;
  const clientConfig = Platform.OS === "ios"
    ? { iosClientId: clientId ?? "" }
    : { webClientId: Platform.OS === "android" ? "" : clientId ?? "" };
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
    if (Platform.OS === "android") {
      return requestAndroidGoogleIdToken(GoogleOneTapSignIn, runtime.googleWebClientId);
    }
    const result = await promptAsync();
    const credential = googleCredentialFromResult(result);
    if (credential === null) {
      throw new GoogleSignInFlowError(googleResultMessage(result));
    }
    return credential;
  }, [available, promptAsync, runtime.googleWebClientId]);

  return { available, ready: Platform.OS === "android" ? available : request !== null, signIn };
}
