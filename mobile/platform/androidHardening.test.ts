import { expect, it } from "vitest";
import type { AndroidManifest } from "expo/config-plugins";

import * as androidHardening from "../plugins/withAndroidHardening";
import {
  ANDROID_BLOCKED_PERMISSIONS,
  FITICIAN_BACKUP_RULES,
  FITICIAN_DATA_EXTRACTION_RULES,
  FITICIAN_DEVELOPMENT_NETWORK_SECURITY_CONFIG,
  FITICIAN_NETWORK_SECURITY_CONFIG,
  applyAndroidSecurityManifest,
  networkSecurityConfigForEnvironment,
  resolveAndroidBuildEnvironment,
} from "../plugins/withAndroidHardening";

type AndroidManifestApplier = (
  manifest: AndroidManifest,
  environment: "development" | "preview" | "production",
) => AndroidManifest;

const applyManifestForEnvironment = applyAndroidSecurityManifest as AndroidManifestApplier;

function manifestWithApplication(): AndroidManifest {
  return {
    manifest: {
      $: {},
      "uses-permission": [{ $: { "android:name": "android.permission.CAMERA" } }],
      application: [{ $: {} }],
    },
  } as unknown as AndroidManifest;
}

it("removes broad storage and overlay permissions from the final Android manifest", () => {
  const manifest = {
    manifest: {
      $: {},
      "uses-permission": [
        { $: { "android:name": "android.permission.CAMERA" } },
        ...ANDROID_BLOCKED_PERMISSIONS.map((name) => ({ $: { "android:name": name } })),
      ],
      application: [{ $: {} }],
    },
  } as unknown as AndroidManifest;

  applyAndroidSecurityManifest(manifest);

  const permissions = manifest.manifest["uses-permission"] as Array<{ $: Record<string, string> }>;
  expect(permissions).toContainEqual({ $: { "android:name": "android.permission.CAMERA" } });
  for (const permission of ANDROID_BLOCKED_PERMISSIONS) {
    expect(permissions).toContainEqual({
      $: { "android:name": permission, "tools:node": "remove" },
    });
  }
  expect(manifest.manifest.application![0].$).toMatchObject({
    "android:allowBackup": "false",
    "android:dataExtractionRules": "@xml/fitician_data_extraction_rules",
    "android:fullBackupContent": "@xml/fitician_backup_rules",
    "android:networkSecurityConfig": "@xml/fitician_network_security_config",
    "android:usesCleartextTraffic": "false",
  });
});

it("excludes all app data from legacy and modern Android backup paths", () => {
  expect(FITICIAN_BACKUP_RULES).toMatch(/<exclude domain="database" path="\."\/>/);
  expect(FITICIAN_BACKUP_RULES).toMatch(/<exclude domain="sharedpref" path="\."\/>/);
  expect(FITICIAN_BACKUP_RULES).toMatch(/<exclude domain="file" path="\."\/>/);
  expect(FITICIAN_DATA_EXTRACTION_RULES).toMatch(/<cloud-backup>/);
  expect(FITICIAN_DATA_EXTRACTION_RULES).toMatch(/<device-transfer>/);
  expect(FITICIAN_DATA_EXTRACTION_RULES).toMatch(/domain="database" path="\."/);
  expect(FITICIAN_DATA_EXTRACTION_RULES).toMatch(/domain="sharedpref" path="\."/);
  expect(FITICIAN_BACKUP_RULES).not.toContain('domain="cache"');
  expect(FITICIAN_BACKUP_RULES).not.toContain('domain="noBackup"');
  expect(FITICIAN_DATA_EXTRACTION_RULES).not.toContain('domain="cache"');
  expect(FITICIAN_DATA_EXTRACTION_RULES).not.toContain('domain="noBackup"');
});

it("requires system-trusted TLS and disallows cleartext traffic in release", () => {
  expect(FITICIAN_NETWORK_SECURITY_CONFIG).toContain("cleartextTrafficPermitted=\"false\"");
  expect(FITICIAN_NETWORK_SECURITY_CONFIG).toContain("certificates src=\"system\"");
  expect(FITICIAN_NETWORK_SECURITY_CONFIG).not.toContain("domain-config");
  expect(FITICIAN_NETWORK_SECURITY_CONFIG).not.toContain("cleartextTrafficPermitted=\"true\"");
});

it("allows cleartext development traffic while retaining the network security resource", () => {
  const manifest = manifestWithApplication();

  applyManifestForEnvironment(manifest, "development");

  expect(manifest.manifest.application![0].$).toMatchObject({
    "android:networkSecurityConfig": "@xml/fitician_network_security_config",
    "android:usesCleartextTraffic": "true",
  });
});

it.each(["preview", "production"] as const)(
  "blocks cleartext traffic for %s builds",
  (environment) => {
    const manifest = manifestWithApplication();

    applyManifestForEnvironment(manifest, environment);

    expect(manifest.manifest.application![0].$).toMatchObject({
      "android:networkSecurityConfig": "@xml/fitician_network_security_config",
      "android:usesCleartextTraffic": "false",
    });
  },
);

it("fails closed to the release policy for an unknown build environment", () => {
  expect(resolveAndroidBuildEnvironment("unexpected")).toBe("production");
});

it("generates a cleartext-enabled development network policy with system trust", () => {
  const policy = networkSecurityConfigForEnvironment("development");

  expect(policy).toBe(FITICIAN_DEVELOPMENT_NETWORK_SECURITY_CONFIG);
  expect(policy).toContain("cleartextTrafficPermitted=\"true\"");
  expect(policy).toContain("certificates src=\"system\"");
});

it.each(["preview", "production"] as const)(
  "generates a system-trusted TLS-only network policy for %s",
  (environment) => {
    const policy = networkSecurityConfigForEnvironment(environment);

    expect(policy).toBe(FITICIAN_NETWORK_SECURITY_CONFIG);
    expect(policy).toContain("cleartextTrafficPermitted=\"false\"");
    expect(policy).toContain("certificates src=\"system\"");
  },
);

for (const language of ["kt", "java"] as const) {
  for (const environment of ["development", "preview", "production"] as const) {
    it.each([false, true])(
      `allows capture for ${language} ${environment} activities (previously blocked: %s)`,
      (previouslyBlocked) => {
        const java = language === "java";
        const original = [
          `import android.os.Bundle${java ? ";" : ""}`,
          ...(previouslyBlocked ? [
            `import android.view.WindowManager${java ? ";" : ""}`,
          ] : []),
          "class MainActivity {",
          java
            ? "  protected void onCreate(Bundle savedInstanceState) {"
            : "  override fun onCreate(savedInstanceState: Bundle?) {",
          ...(previouslyBlocked ? [
            `    ${androidHardening.SCREENSHOT_POLICY_MARKER}`,
            java
              ? "    getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);"
              : "    window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)",
          ] : []),
          "    // Preserve other activity setup",
          "  }",
          "}",
        ].join("\n");
        const project = androidHardening.applyAndroidScreenshotPolicy(
          { language, contents: original }, environment,
        );
        expect(project.contents).not.toContain("FLAG_SECURE");
        expect(project.contents).not.toContain(androidHardening.SCREENSHOT_POLICY_MARKER);
        expect(project.contents).not.toContain("import android.view.WindowManager");
        expect(project.contents).toContain("// Preserve other activity setup");
        expect(androidHardening.applyAndroidScreenshotPolicy(
          { ...project }, environment,
        ).contents).toBe(project.contents);
        if (!previouslyBlocked) expect(project.contents).toBe(original);
      },
    );
  }
}

it("preserves unrelated WindowManager usage when removing the old capture block", () => {
  const project = androidHardening.applyAndroidScreenshotPolicy({
    language: "kt",
    contents: [
      "import android.view.WindowManager",
      androidHardening.SCREENSHOT_POLICY_MARKER,
      "window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)",
      "window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)",
    ].join("\n"),
  }, "production");
  expect(project.contents).not.toContain("FLAG_SECURE");
  expect(project.contents).toContain("import android.view.WindowManager");
  expect(project.contents).toContain("window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)");
});
