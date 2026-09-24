import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";
import { parseEnvFile, validateEnvironment } from "./environment.mjs";

const mobileRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("parses and validates each Fitician mobile environment", () => {
  const values = parseEnvFile(
    "APP_VARIANT=preview\nEXPO_PUBLIC_API_BASE_URL=https://api-preview.fitician.example\nEXPO_PUBLIC_FRONTEND_ORIGIN=https://preview.fitician.example\nEXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID=\nFITICIAN_APP_LINK_HOST=preview.fitician.example\n",
  );

  assert.equal(values.APP_VARIANT, "preview");
  assert.doesNotThrow(() => validateEnvironment("preview", values));
  assert.doesNotThrow(() => validateEnvironment("production", {
    ...values,
    APP_VARIANT: "production",
    EXPO_PUBLIC_API_BASE_URL: "https://fitician.fit",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://fitician.fit",
    VITE_MEDIA_PUBLIC_BASE_URL: "https://media.fitician.example",
    FITICIAN_APP_LINK_HOST: "fitician.fit",
  }));
});

test("rejects every forbidden production endpoint class", () => {
  const base = {
    APP_VARIANT: "production",
    EXPO_PUBLIC_API_BASE_URL: "https://fitician.fit",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://fitician.fit",
    VITE_MEDIA_PUBLIC_BASE_URL: "https://media.example.test",
    FITICIAN_APP_LINK_HOST: "fitician.fit",
  };

  for (const rejected of [
    "http://fitician.fit",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://10.0.2.2:8001",
    "http://192.168.1.5:8001",
    "http://172.16.0.5:8001",
    "http://100.97.78.5:8001",
    "https://backend.local",
    "https://api.fitician.example",
  ]) {
    assert.throws(
      () => validateEnvironment("production", {
        ...base,
        EXPO_PUBLIC_API_BASE_URL: rejected,
      }),
      /approved production origin/u,
    );
  }

  assert.throws(
    () => validateEnvironment("production", {
      ...base,
      FITICIAN_APP_LINK_HOST: "app.fitician.example",
    }),
    /FITICIAN_APP_LINK_HOST must be fitician\.fit/u,
  );
});

test("documents the exact public production environment", async () => {
  const example = await readFile(resolve(mobileRoot, ".env.production.example"), "utf8");
  const schema = await readFile(resolve(mobileRoot, "config/environment.schema.json"), "utf8");
  const values = parseEnvFile(example);

  assert.equal(values.APP_VARIANT, "production");
  assert.equal(values.EXPO_PUBLIC_API_BASE_URL, "https://fitician.fit");
  assert.equal(values.EXPO_PUBLIC_FRONTEND_ORIGIN, "https://fitician.fit");
  assert.equal(values.FITICIAN_APP_LINK_HOST, "fitician.fit");
  assert.equal(values.VITE_MEDIA_PUBLIC_BASE_URL, "");
  assert.match(
    example,
    /same public media base currently used by Web\/CI through the repository variable VITE_MEDIA_PUBLIC_BASE_URL/u,
  );
  assert.doesNotMatch(example, /EXPO_PUBLIC_MEDIA_PUBLIC_BASE_URL/u);
  assert.doesNotMatch(schema, /EXPO_PUBLIC_MEDIA_PUBLIC_BASE_URL/u);
});

test("validates the shared public media base by environment", () => {
  const base = {
    APP_VARIANT: "production",
    EXPO_PUBLIC_API_BASE_URL: "https://fitician.fit",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://fitician.fit",
    FITICIAN_APP_LINK_HOST: "fitician.fit",
  };

  assert.doesNotThrow(() => validateEnvironment("production", {
    ...base,
    VITE_MEDIA_PUBLIC_BASE_URL: "  https://media.example.test/assets///  ",
  }));
  assert.doesNotThrow(() => validateEnvironment("preview", {
    APP_VARIANT: "preview",
    EXPO_PUBLIC_API_BASE_URL: "https://api-preview.fitician.example",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://preview.fitician.example",
    FITICIAN_APP_LINK_HOST: "preview.fitician.example",
    VITE_MEDIA_PUBLIC_BASE_URL: "https://media.example.test",
  }));
  assert.throws(() => validateEnvironment("preview", {
    APP_VARIANT: "preview",
    EXPO_PUBLIC_API_BASE_URL: "https://api-preview.fitician.example",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://preview.fitician.example",
    FITICIAN_APP_LINK_HOST: "preview.fitician.example",
    VITE_MEDIA_PUBLIC_BASE_URL: "http://media.example.test",
  }), /VITE_MEDIA_PUBLIC_BASE_URL/u);
  assert.throws(() => validateEnvironment("preview", {
    APP_VARIANT: "preview",
    EXPO_PUBLIC_API_BASE_URL: "https://api-preview.fitician.example",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://preview.fitician.example",
    FITICIAN_APP_LINK_HOST: "preview.fitician.example",
    VITE_MEDIA_PUBLIC_BASE_URL: "////",
  }), /VITE_MEDIA_PUBLIC_BASE_URL/u);
  for (const invalid of [
    "http://media.example.test",
    "//media.example.test/assets",
    "javascript:alert(1)",
    "file:///media",
    "data:image/png;base64,abc",
  ]) {
    assert.throws(() => validateEnvironment("production", {
      ...base,
      VITE_MEDIA_PUBLIC_BASE_URL: invalid,
    }), /VITE_MEDIA_PUBLIC_BASE_URL/u);
  }
  assert.throws(() => validateEnvironment("production", base), /VITE_MEDIA_PUBLIC_BASE_URL/u);
  assert.doesNotThrow(() => validateEnvironment("development", {
    APP_VARIANT: "development",
    EXPO_PUBLIC_API_BASE_URL: "http://10.0.2.2:8001",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "http://localhost:5173",
    FITICIAN_APP_LINK_HOST: "app.fitician.example",
  }));
  assert.doesNotThrow(() => validateEnvironment("production", base, { allowPlaceholder: true }));
});

test("requires a trusted HTTPS frontend origin outside development", () => {
  assert.throws(
    () =>
      validateEnvironment("preview", {
        APP_VARIANT: "preview",
        EXPO_PUBLIC_API_BASE_URL: "https://api-preview.fitician.example",
        EXPO_PUBLIC_FRONTEND_ORIGIN: "http://preview.fitician.example",
        FITICIAN_APP_LINK_HOST: "preview.fitician.example",
      }),
    /EXPO_PUBLIC_FRONTEND_ORIGIN must use HTTPS outside development/,
  );
});

test("validates each configured Google client ID without blocking the other platform", () => {
  const base = {
    APP_VARIANT: "preview",
    EXPO_PUBLIC_API_BASE_URL: "https://api-preview.fitician.example",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://preview.fitician.example",
    FITICIAN_APP_LINK_HOST: "preview.fitician.example",
  };

  assert.doesNotThrow(() => validateEnvironment("preview", {
    ...base,
    EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID: "android.apps.googleusercontent.com",
  }));
  assert.throws(
    () => validateEnvironment("preview", {
      ...base,
      EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID: "android-client",
      EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID: "ios-client",
    }),
    /must be a Google OAuth client ID/u,
  );
  assert.doesNotThrow(() => validateEnvironment("preview", {
    ...base,
    EXPO_PUBLIC_GOOGLE_ANDROID_CLIENT_ID: "android.apps.googleusercontent.com",
    EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID: "ios.apps.googleusercontent.com",
    EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: "web.apps.googleusercontent.com",
  }));
  assert.throws(() => validateEnvironment("preview", {
    ...base,
    EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID: "web-client",
  }), /EXPO_PUBLIC_GOOGLE_WEB_CLIENT_ID must be a Google OAuth client ID/u);
});

test("requires the iOS Google client ID for release environments", () => {
  const base = {
    APP_VARIANT: "preview",
    EXPO_PUBLIC_API_BASE_URL: "https://api-preview.fitician.example",
    EXPO_PUBLIC_FRONTEND_ORIGIN: "https://preview.fitician.example",
    FITICIAN_APP_LINK_HOST: "preview.fitician.example",
  };

  assert.throws(
    () => validateEnvironment("preview", base, { requireGoogleIosClientId: true }),
    /EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID is required/u,
  );
  assert.doesNotThrow(() => validateEnvironment("preview", {
    ...base,
    EXPO_PUBLIC_GOOGLE_IOS_CLIENT_ID: "ios.apps.googleusercontent.com",
  }, { requireGoogleIosClientId: true }));
  assert.doesNotThrow(() => validateEnvironment("preview", base, {
    allowPlaceholder: true,
    requireGoogleIosClientId: true,
  }));
});

test("documents emulator and physical Android development API targets", async () => {
  const example = await readFile(resolve(mobileRoot, ".env.development.example"), "utf8");

  assert.match(example, /10\.0\.2\.2:8001/u);
  assert.match(example, /physical Android|LAN|Tailscale|laptop/i);
  assert.match(example, /<[^>]*(?:LAN|TAILSCALE|LAPTOP)[^>]*>.*:8001/iu);
});
