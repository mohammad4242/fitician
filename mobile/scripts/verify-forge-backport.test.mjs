import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { verifyForgeBackport } from "./verify-forge-backport.mjs";
const require = createRequire(import.meta.url);
test("all Expo signing consumers reject CVE-2026-85393 and match reviewed source", verifyForgeBackport);
test("backport preserves ordinary RSA signing and certificate operations", () => {
  const certificates = require("@expo/code-signing-certificates");
  const forge = createRequire(require.resolve("@expo/code-signing-certificates/package.json"))("node-forge");
  const keys = forge.pki.rsa.generateKeyPair({ bits: 1024 });
  const md = forge.md.sha256.create(); md.update("Fitician signing compatibility");
  const signature = keys.privateKey.sign(md);
  assert.equal(keys.publicKey.verify(md.digest().getBytes(), signature), true);
  assert.equal(typeof certificates.generateKeyPair, "function");
  // Exercise the normal verification path with and without optional NULL.
  const { asn1 } = forge;
  const oid = asn1.create(asn1.Class.UNIVERSAL, asn1.Type.OID, false,
    asn1.oidToDer(forge.pki.oids.sha256).getBytes());
  for (const parameters of [[], [asn1.create(asn1.Class.UNIVERSAL, asn1.Type.NULL, false, "")]]) {
    const algorithm = asn1.create(asn1.Class.UNIVERSAL, asn1.Type.SEQUENCE, true, [oid, ...parameters]);
    const info = asn1.create(asn1.Class.UNIVERSAL, asn1.Type.SEQUENCE, true, [algorithm,
      asn1.create(asn1.Class.UNIVERSAL, asn1.Type.OCTETSTRING, false, md.digest().getBytes())]);
    assert.equal(keys.publicKey.verify(md.digest().getBytes(), keys.privateKey.sign(asn1.toDer(info).getBytes(), "NONE")), true);
    algorithm.value.push(asn1.create(asn1.Class.UNIVERSAL, asn1.Type.OCTETSTRING, false, "garbage"));
    assert.throws(() => keys.publicKey.verify(md.digest().getBytes(), keys.privateKey.sign(asn1.toDer(info).getBytes(), "NONE")),
      /valid RSASSA-PKCS1-v1_5 DigestInfo/);
  }
  const cert = forge.pki.createCertificate(); cert.publicKey = keys.publicKey;
  cert.serialNumber = "01"; cert.validity.notBefore = new Date();
  cert.validity.notAfter = new Date(Date.now() + 86400000);
  cert.setSubject([{ name: "commonName", value: "Fitician regression fixture" }]);
  cert.setIssuer(cert.subject.attributes); cert.sign(keys.privateKey, forge.md.sha256.create());
  assert.equal(forge.pki.certificateFromPem(forge.pki.certificateToPem(cert)).verify(cert), true);
});
