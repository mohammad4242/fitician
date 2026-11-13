import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";

export function sentryReleaseEnvironment(env) {
  if (!env.EXPO_PUBLIC_SENTRY_DSN) return { SENTRY_DISABLE_AUTO_UPLOAD: "1" };
  const commit = env.EAS_BUILD_GIT_COMMIT_HASH || env.EXPO_PUBLIC_APP_BUILD_SHA;
  if (typeof commit !== "string" || !/^[a-f0-9]{40}$/.test(commit)) {
    throw new Error("exact_mobile_release_commit_required");
  }
  if (env.EAS_BUILD_GIT_COMMIT_HASH && env.EXPO_PUBLIC_APP_BUILD_SHA
    && env.EAS_BUILD_GIT_COMMIT_HASH !== env.EXPO_PUBLIC_APP_BUILD_SHA) {
    throw new Error("mobile_release_commit_mismatch");
  }
  if (!env.SENTRY_AUTH_TOKEN || !env.SENTRY_ORG || !env.SENTRY_PROJECT) {
    throw new Error("private_mobile_artifact_upload_not_configured");
  }
  return { SENTRY_RELEASE: `fitician-mobile@${commit}`, EXPO_PUBLIC_APP_BUILD_SHA: commit };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const values = sentryReleaseEnvironment(process.env);
  if (process.env.EAS_BUILD === "true") {
    for (const [name, value] of Object.entries(values)) {
      // Only public release metadata is passed to set-env, never the upload credential.
      const result = spawnSync("set-env", [name, value], { stdio: "pipe" });
      if (result.status !== 0) throw new Error("mobile_build_release_environment_not_applied");
    }
  }
}
