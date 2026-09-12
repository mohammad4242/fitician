/* oxlint-disable react/only-export-components -- provider and its hook form one public boundary */
import {
  createContext,
  type ReactNode,
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

import { useAuth } from "../auth/AuthContext";
import * as api from "./api";

export type EntitlementContextValue = {
  snapshot: EntitlementSnapshot | null;
  loading: boolean;
  error: unknown | null;
  retry: () => void;
  hasEntitlement: (entitlement: EntitlementCode) => boolean;
  quotaFor: (entitlement: EntitlementCode) => QuotaStatus | null;
};

const EntitlementContext = createContext<EntitlementContextValue | null>(null);

type InFlightRequest = {
  userId: string;
  promise: Promise<EntitlementSnapshot>;
};

export function EntitlementProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const userId = user?.id ?? null;
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
      : api.getEntitlementSnapshot();
    if (existingRequest?.userId !== userId) {
      inFlightRequest.current = { userId, promise };
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
  }, [retryAttempt, userId]);

  const value = useMemo<EntitlementContextValue>(
    () => ({
      snapshot,
      loading,
      error,
      retry: () => setRetryAttempt((attempt) => attempt + 1),
      hasEntitlement: (entitlement) => snapshot?.entitlements.granted.includes(entitlement) ?? false,
      quotaFor: (entitlement) => snapshot?.entitlements.quotas.find(
        (quota) => quota.entitlement === entitlement,
      ) ?? null,
    }),
    [error, loading, snapshot],
  );

  return <EntitlementContext.Provider value={value}>{children}</EntitlementContext.Provider>;
}

export function useEntitlements(): EntitlementContextValue {
  const context = useContext(EntitlementContext);
  if (context === null) {
    throw new Error("useEntitlements must be used within EntitlementProvider");
  }
  return context;
}
