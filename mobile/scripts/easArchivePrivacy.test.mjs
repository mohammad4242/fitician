import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import ignore from "ignore";

test("EAS archives exclude local secrets and signing credentials at every depth", async () => {
  const rules = ignore().add(await readFile(new URL("../../.easignore", import.meta.url), "utf8"));
  const privateFiles = [
    ".env", ".env.local", ".env.production", "mobile/.env.local", "mobile/.env.production",
    "mobile/credentials.json", "mobile/signing/release.jks", "mobile/signing/release.keystore",
    "mobile/signing/apple.p8", "mobile/signing/apple.p12", "mobile/signing/profile.mobileprovision",
    ".codex-tmp/sentry-setup/automation-tokens.json", "backend/.env", "mobile/signing/private.key",
  ];
  for (const filename of privateFiles) assert.equal(rules.ignores(filename), true, filename);
  for (const filename of ["mobile/app.config.ts", "mobile/assets/branding/fitician-icon.png", "packages/fitician-core/src/index.ts"]) {
    assert.equal(rules.ignores(filename), false, filename);
  }
});
