import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "node:test";

import { validateReleaseConfig } from "./validate-release-config.mjs";

const mobileRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");

test("keeps EAS profiles isolated and remotely signed", async () => {
  const easConfig = JSON.parse(await readFile(resolve(mobileRoot, "eas.json"), "utf8"));
  const appConfig = await readFile(resolve(mobileRoot, "app.config.ts"), "utf8");

  assert.doesNotThrow(() => validateReleaseConfig(easConfig, appConfig));
  for (const [name, profile] of Object.entries(easConfig.build)) {
    if (name !== "production-device") {
      assert.equal(profile.ios?.credentialsSource, "remote", `${name} iOS signing drifted`);
    }
    assert.equal(profile.distribution, name === "production" ? "store" : "internal");
    assert.equal(profile.env?.APP_VARIANT, name === "production-device" ? "production" : name);
  }
  assert.deepEqual(easConfig.build["production-device"], {
    extends: "production",
    autoIncrement: false,
    distribution: "internal",
    environment: "production",
    env: { APP_VARIANT: "production" },
    android: { buildType: "apk", credentialsSource: "remote" },
  });
  assert.ok(easConfig.submit?.production?.ios);
});

test("rejects a release profile without remote iOS signing", async () => {
  const easConfig = JSON.parse(await readFile(resolve(mobileRoot, "eas.json"), "utf8"));
  const appConfig = await readFile(resolve(mobileRoot, "app.config.ts"), "utf8");
  delete easConfig.build.preview.ios;

  assert.throws(
    () => validateReleaseConfig(easConfig, appConfig),
    /preview iOS credentials/u,
  );
});
