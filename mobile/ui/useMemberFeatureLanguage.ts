import { useEffect, useSyncExternalStore } from "react";
import * as SecureStore from "expo-secure-store";
import { languageForDirection, type MobileLanguage } from "./rtl";
// Support and Progress share this presentation preference without changing legacy flows.
const key = "fitician.member-feature-language";
let selected: MobileLanguage | null = null;
let hydrated = false;
const listeners = new Set<() => void>();
const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
};
const snapshot = () => selected ?? languageForDirection();
export function useMemberFeatureLanguage(): readonly [
  MobileLanguage,
  (language: MobileLanguage) => void,
] {
  const language = useSyncExternalStore(subscribe, snapshot, snapshot);
  useEffect(() => {
    if (hydrated) return;
    hydrated = true;
    void SecureStore.getItemAsync(key)
      .then((value) => {
        if (selected === null && (value === "fa" || value === "en")) {
          selected = value;
          listeners.forEach((listener) => listener());
        }
      })
      .catch(() => undefined);
  }, []);
  const change = (value: MobileLanguage) => {
    selected = value;
    listeners.forEach((listener) => listener());
    void SecureStore.setItemAsync(key, value).catch(() => undefined);
  };
  return [language, change];
}
