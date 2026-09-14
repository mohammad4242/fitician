import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, Outlet } from "react-router-dom";

import { ApiError, type ErrorAudienceInput, type ErrorContext } from "@fitician/core";

import { AppErrorNotice } from "../../shared/AppErrorNotice";
import { useAuth } from "../auth/AuthContext";
import { HYDRATED_ACCOUNT_KEY } from "../publicOnboarding/onboardingDraft";
import { verifyPhysicianAccess } from "../nutrition/api";
import { verifyCoachAccess } from "../workoutReviews/api";
import { useProfile, type ProfileStatus } from "./ProfileContext";

function StartupState({
  error,
  onRetry,
  audience = "member",
  context = "profile",
}: {
  error: unknown;
  onRetry: () => void;
  audience?: ErrorAudienceInput;
  context?: ErrorContext;
}) {
  const { t, i18n } = useTranslation();

  if (error) {
    return (
      <main className="loading-screen">
        <AppErrorNotice
          audience={audience}
          context={context}
          error={error}
          locale={i18n.resolvedLanguage === "en" ? "en" : "fa"}
        />
        <button className="retry-button" type="button" onClick={onRetry}>
          {t("common.retry")}
        </button>
      </main>
    );
  }

  return (
    <main className="loading-screen" aria-live="polite">
      <span className="loading-mark" aria-hidden="true" />
      <p>{t("common.loading")}</p>
    </main>
  );
}

function profileStartupState(status: ProfileStatus, retryProfile: () => void, profileError: unknown) {
  if (status === "idle" || status === "loading") {
    return <StartupState error={null} onRetry={retryProfile} />;
  }
  if (status === "error") {
    return <StartupState error={profileError} onRetry={retryProfile} />;
  }
  return null;
}

export function GuestRoute() {
  const { user, loading, startupError, retryStartup } = useAuth();
  const { status, profileError, retryProfile } = useProfile();

  if (loading || startupError) {
    return <StartupState error={startupError} onRetry={retryStartup} />;
  }
  if (user === null) {
    return <Outlet />;
  }

  const startupState = profileStartupState(status, retryProfile, profileError);
  if (startupState !== null) {
    return startupState;
  }

  return <Navigate to={status === "missing" ? "/onboarding" : "/dashboard"} replace />;
}

export function OnboardingRoute() {
  const { status, profileError, retryProfile } = useProfile();
  const startupState = profileStartupState(status, retryProfile, profileError);

  if (startupState !== null) {
    return startupState;
  }

  return status === "missing" || status === "mode_selected" ? <Outlet /> : <Navigate to="/dashboard" replace />;
}

export function CompletedProfileRoute() {
  const { status, profileError, retryProfile } = useProfile();
  const startupState = profileStartupState(status, retryProfile, profileError);

  if (startupState !== null) {
    return startupState;
  }

  const hasJustHydratedAccount = sessionStorage.getItem(HYDRATED_ACCOUNT_KEY) === "true";
  return status === "missing" && !hasJustHydratedAccount
    ? <Navigate to="/onboarding" replace />
    : <Outlet />;
}

export function NutritionCapabilityRoute() {
  const { productMode } = useProfile();
  return productMode === "nutrition" || productMode === "both"
    ? <Outlet />
    : <Navigate to="/dashboard" replace />;
}

type SpecialistAccessStatus = "loading" | "authorized" | "denied" | "error";

function SpecialistAccessRoute({
  audience,
  verifyAccess,
}: {
  audience: "coach" | "physician";
  verifyAccess: () => Promise<{ authorized: true }>;
}) {
  const [status, setStatus] = useState<SpecialistAccessStatus>("loading");
  const [error, setError] = useState<unknown>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setStatus("loading");
    setError(null);
    void verifyAccess()
      .then(() => { if (active) setStatus("authorized"); })
      .catch((cause: unknown) => {
        if (!active) return;
        if (cause instanceof ApiError && cause.status === 403) {
          setStatus("denied");
          return;
        }
        setError(cause);
        setStatus("error");
      });
    return () => { active = false; };
  }, [attempt, verifyAccess]);
  if (status === "loading") return <StartupState error={null} onRetry={() => undefined} />;
  if (status === "error") {
    return (
      <StartupState
        audience={audience}
        context="specialist_review"
        error={error}
        onRetry={() => setAttempt((value) => value + 1)}
      />
    );
  }
  return status === "authorized" ? <Outlet /> : <Navigate to="/dashboard" replace />;
}

export function PhysicianRoute() {
  return <SpecialistAccessRoute audience="physician" verifyAccess={verifyPhysicianAccess} />;
}

export function CoachRoute() {
  return <SpecialistAccessRoute audience="coach" verifyAccess={verifyCoachAccess} />;
}
