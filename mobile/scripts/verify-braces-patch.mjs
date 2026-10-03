import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(import.meta.url);

export function verifyBracesPatch() {
  const installed = dirname(require.resolve("braces/package.json"));
  assert.equal(lstatSync(installed).isSymbolicLink(), false, "Patch must remain visible to npm audit");
  const metadata = JSON.parse(readFileSync(resolve(installed, "package.json"), "utf8"));
  assert.equal(metadata.name, "braces");
  assert.equal(metadata.version, "3.0.4-fitician.1");
  const integrity = JSON.parse(readFileSync(resolve(root, "vendor/braces/integrity.json"), "utf8"));
  for (const [path, expected] of Object.entries(integrity)) {
    assert.equal(createHash("sha256").update(readFileSync(resolve(installed, path))).digest("hex"), expected,
      `Installed braces differs from reviewed source: ${path}`);
  }
  const consumer = createRequire(require.resolve("micromatch/package.json"));
  assert.equal(realpathSync(consumer.resolve("braces")), realpathSync(resolve(installed, "index.js")));
  const braces = consumer("braces");
  const pattern = "{".repeat(4000) + "a" + "}".repeat(4000);
  for (const method of ["parse", "compile", "expand", "stringify"]) {
    assert.throws(() => braces[method](pattern), { name: "SyntaxError", message: /nesting depth/ });
  }
}
