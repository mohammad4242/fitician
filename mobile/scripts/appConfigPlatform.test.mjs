import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";

function loadConfig(platform, variant, googleIosClientId = "", overrides = {}) {
  return spawnSync(process.execPath, ["--input-type=module", "-e", `
    import { loadModuleSync } from '@expo/require-utils';
    import { resolve } from 'node:path';
    const { default: config } = loadModuleSync(resolve('app.config.ts'));
    console.log(JSON.stringify({
      name: config.name,
      version: config.version,
      package: config.android.package,
      autolinking: config.autolinking,
      plugins: config.plugins.map((plugin) =>
        Array.isArray(plugin) ? plugin[0] : typeof plugin === "string" ? plugin : "custom",
      ),
      environment: config.extra.environment,
      apiBaseUrl: config.extra.apiBaseUrl,
      frontendOrigin: config.extra.frontendOrigin,
      appLinkHost: config.extra.appLinkHost,
    }));
  `], {
    cwd: new URL("../", import.meta.url),
    encoding: "utf8",
    env: {
      ...process.env,
      EAS_BUILD_PLATFORM: platform,
      APP_VARIANT: variant,
      EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID: googleIosClientId,
      EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID: "android.apps.googleusercontent.com",
      EXPO_PUBLIC_API_BASE_URL: "https://api.example.com",
      EXPO_PUBLIC_FRONTEND_ORIGIN: "https://app.example.com",
      FITICIAN_APP_LINK_HOST: "app.example.com",
      ...overrides,
    },
  });
}

function loadNativeConfig(variant) {
  return spawnSync(process.execPath, ["--input-type=module", "-e", `
    const { default: config } = await import('./react-native.config.js');
    console.log(JSON.stringify(config));
  `], {
    cwd: new URL("../", import.meta.url),
    encoding: "utf8",
    env: { ...process.env, APP_VARIANT: variant },
  });
}

test("Android preview config does not require credentials for iOS Google login", () => {
  const result = loadConfig("android", "preview");
  assert.equal(result.status, 0, result.stderr);
});

test("iOS preview still requires Google client configuration", () => {
  const result = loadConfig("ios", "preview");
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID is required/u);
  const configured = loadConfig("ios", "preview", "ios.apps.googleusercontent.com");
  assert.equal(configured.status, 0, configured.stderr);
});

test("development config can build before Google credentials are provisioned", () => {
  const result = loadConfig("ios", "development");
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /com\.fitician\.app/u);
  assert.match(result.stdout, /expo-dev-client/u);
});

test("release configs do not include the Expo development client", () => {
  for (const variant of ["preview", "production"]) {
    const result = loadConfig("android", variant, "", variant === "production"
      ? {
          EXPO_PUBLIC_API_BASE_URL: "https://fitician.fit",
          EXPO_PUBLIC_FRONTEND_ORIGIN: "https://fitician.fit",
          FITICIAN_APP_LINK_HOST: "fitician.fit",
        }
      : undefined);
    assert.equal(result.status, 0, result.stderr);
    const resolved = JSON.parse(result.stdout);
    assert.equal(resolved.plugins.includes("expo-dev-client"), false);
  }
});

test("release native autolinking excludes the Expo development client", () => {
  const production = loadNativeConfig("production");
  assert.equal(production.status, 0, production.stderr);
  assert.deepEqual(JSON.parse(production.stdout), {
    dependencies: {
      "expo-dev-client": { platforms: { android: null, ios: null } },
    },
  });

  const development = loadNativeConfig("development");
  assert.equal(development.status, 0, development.stderr);
  assert.deepEqual(JSON.parse(development.stdout), { dependencies: { "expo-dev-client": {} } });
});

test("Android production resolves only the approved public runtime", () => {
  const production = {
    EXPO_PUBLIC_API_BASE_URL: "https://fitician.fit",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://fitician.fit",
    FITICIAN_APP_LINK_HOST: "fitician.fit",
  };
  const result = loadConfig("android", "production", "", production);
  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(JSON.parse(result.stdout), {
    name: "Fitician",
    version: "0.1.0",
    package: "com.fitician.app",
    autolinking: { exclude: ["expo-dev-client"] },
    plugins: [
      "expo-router",
      "expo-web-browser",
      "expo-apple-authentication",
      "expo-splash-screen",
      "expo-font",
      "expo-secure-store",
      "expo-sqlite",
      "expo-image-picker",
      "expo-background-task",
      "expo-notifications",
      "expo-updates",
      "expo-video",
      "expo-build-properties",
      "custom",
      "custom",
      "custom",
      "custom",
    ],
    environment: "production",
    apiBaseUrl: "https://fitician.fit",
    frontendOrigin: "https://fitician.fit",
    appLinkHost: "fitician.fit",
  });

  for (const appLinkHost of ["app.fitician.example", "localhost", "100.97.78.5"]) {
    const rejected = loadConfig("android", "production", "", {
      ...production,
      FITICIAN_APP_LINK_HOST: appLinkHost,
    });
    assert.notEqual(rejected.status, 0);
    assert.match(rejected.stderr, /FITICIAN_APP_LINK_HOST/u);
  }
});
