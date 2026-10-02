import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { lstatSync, readFileSync, realpathSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "../..");
const require = createRequire(import.meta.url);
const vendor = resolve(root, "vendor/node-forge");
// Exact public test fixture from digitalbazaar/forge PR #1152, commit ceba344.
const modulus = "E932AC92252F585B3A80A4DD76A897C8B7652952FE788F6EC8DD640587A1EE5647670A8AD4C2BE0F9FA6E49C605ADF77B5174230AF7BD50E5D6D6D6D28CCF0A886A514CC72E51D209CC772A52EF419F6A953F3135929588EBE9B351FCA61CED78F346FE00DBB6306E5C2A4C6DFC3779AF85AB417371CF34D8387B9B30AE46D7A5FF5A655B8D8455F1B94AE736989D60A6F2FD5CADBFFBD504C5A756A2E6BB5CECC13BCA7503F6DF8B52ACE5C410997E98809DB4DC30D943DE4E812A47553DCE54844A78E36401D13F77DC650619FED88D8B3926E3D8E319C80C744779AC5D6ABE252896950917476ECE5E8FC27D5F053D6018D91B502C4787558A002B9283DA7";
const signature = "a4ae63dd5e7712b78f4870d0f51e294df5503d4f16c5d27ae33370981fb57f0de49f50f3d6a04666774cd984cd13972db9bf8e12bd294ef0ddc916c7c86cbae63efd7b6b97885e69760c208a40f1aecc76a90d7af5145177efce1bb55807a8d05c20b1596753ba710642fc9acdde6c160232654662c77cc4466c8257a38edb49f894e8845d0fd987b857ced88f4b62505a080bd87ef700d35d392a6e8f6fde34250c50b86fae606cb551215e8f4813239b77651d5565ad453698c071d48c31e8e526fb4a37610f64b3e1fb8e5be5898e408ad08197a0947794a530b54f84485377ce4a7488ed485ce4e5e105dd89698a472f390c3b1b76bc16b73276c4d1c81d";

export function verifyForgeBackport() {
  const installed = dirname(require.resolve("node-forge/package.json"));
  assert.equal(lstatSync(installed).isSymbolicLink(), false, "Backport must remain visible to npm audit");
  const metadata = JSON.parse(readFileSync(resolve(installed, "package.json"), "utf8"));
  assert.equal(metadata.name, "node-forge");
  assert.equal(metadata.version, "1.4.1-fitician.1");
  const integrity = JSON.parse(readFileSync(resolve(vendor, "integrity.json"), "utf8"));
  for (const [path, expected] of Object.entries(integrity)) {
    assert.equal(createHash("sha256").update(readFileSync(resolve(installed, path))).digest("hex"), expected);
  }
  const expoRequire = createRequire(require.resolve("expo/package.json"));
  const cliRequire = createRequire(expoRequire.resolve("@expo/cli/package.json"));
  const certificatesRequire = createRequire(require.resolve("@expo/code-signing-certificates/package.json"));
  const updatesRequire = createRequire(require.resolve("expo-updates/package.json"));
  const updatesCertificates = createRequire(updatesRequire.resolve("@expo/code-signing-certificates/package.json"));
  for (const consumer of [cliRequire, certificatesRequire, updatesCertificates]) {
    assert.equal(realpathSync(consumer.resolve("node-forge")), realpathSync(resolve(installed, "lib/index.js")));
    const forge = consumer("node-forge");
    const key = forge.pki.rsa.setPublicKey(new forge.jsbn.BigInteger(modulus, 16), new forge.jsbn.BigInteger("3"));
    const md = forge.md.sha256.create();
    md.update("hello world!");
    assert.throws(() => key.verify(md.digest().getBytes(), forge.util.hexToBytes(signature), undefined,
      { _skipPaddingChecks: true }), /valid RSASSA-PKCS1-v1_5 DigestInfo/);
  }
}
