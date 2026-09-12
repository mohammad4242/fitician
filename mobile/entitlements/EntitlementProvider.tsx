/* oxlint-disable react/only-export-components -- provider and its hook form one public boundary */
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import type {
  EntitlementCode,
  EntitlementSnapshot,
  QuotaStatus,
} from "@fitician/core/entitlements";

import { useMobileAuth } from "../auth/MobileAuthProvider";
import { createEntitlementApi } from "./entitlementApi";

export interface EntitlementContextValue {
  readonly snapshot: EntitlementSnapshot | null;
  readonly loading: boolean;
  readonly error: unknown | null;
  readonly retry: () => void;
  readonly refresh: () => void;
  readonly hasEntitlement: (entitlement: EntitlementCode) => boolean;
  readonly quotaFor: (entitlement: EntitlementCode) => QuotaStatus | null;
}

const EntitlementContext = createContext<EntitlementContextValue | null>(null);

type InFlightRequest = {
  readonly userId: string;
  readonly promise: Promise<EntitlementSnapshot>;
};

export function EntitlementProvider({ children }: { readonly children: ReactNode }) {
  const auth = useMobileAuth();
  const userId = auth.status === "signed_in" ? auth.user?.id ?? null : null;
  const api = useMemo(() => createEntitlementApi(auth.request), [auth.request]);
  const [snapshot, setSnapshot] = useState<EntitlementSnapshot | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<unknown | null>(null);
  const [retryAttempt, setRetryAttempt] = useState(0);
  const requestGeneration = useRef(0);
  const loadedUserId = useRef<string | null>(null);
  const inFlightRequest = useRef<InFlightRequest | null>(null);

  useEffect(() => {
    const generation = ++requestGeneration.current;
    let active = true;

    if (userId === null) {
      loadedUserId.current = null;
      inFlightRequest.current = null;
      setSnapshot(null);
      setError(null);
      setLoading(false);
      return () => {
        active = false;
      };
    }

    if (loadedUserId.current === userId && retryAttempt === 0) {
      setLoading(false);
      return () => {
        active = false;
      };
    }

    setLoading(true);
    setError(null);
    const existingRequest = inFlightRequest.current;
    const promise = existingRequest?.userId === userId
      ? existingRequest.promise
      : api.getSnapshot();
    if (existingRequest?.userId !== userId) {
      inFlightRequest.current = { promise, userId };
    }

    void promise
      .then((nextSnapshot) => {
        if (active && generation === requestGeneration.current) {
          loadedUserId.current = userId;
          setSnapshot(nextSnapshot);
          setError(null);
        }
      })
      .catch((nextError: unknown) => {
        if (active && generation === requestGeneration.current) {
          loadedUserId.current = null;
          setSnapshot(null);
          setError(nextError);
        }
      })
      .finally(() => {
        if (inFlightRequest.current?.promise === promise) {
          inFlightRequest.current = null;
        }
        if (active && generation === requestGeneration.current) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [api, retryAttempt, userId]);

  const retry = useCallback(() => {
    setRetryAttempt((attempt) => attempt + 1);
  }, []);
  const value = useMemo<EntitlementContextValue>(
    () => ({
      snapshot,
      loading,
      error,
      retry,
      refresh: retry,
      hasEntitlement: (entitlement) => snapshot?.entitlements.granted.includes(entitlement) ?? false,
      quotaFor: (entitlement) => snapshot?.entitlements.quotas.find(
        (quota) => quota.entitlement === entitlement,
      ) ?? null,
    }),
    [error, loading, retry, snapshot],
  );

  return <EntitlementContext.Provider value={value}>{children}</EntitlementContext.Provider>;
}

export function useMobileEntitlements(): EntitlementContextValue {
  const context = useContext(EntitlementContext);
  if (context === null) {
    throw new Error("useMobileEntitlements must be used within EntitlementProvider");
  }
  return context;
}
