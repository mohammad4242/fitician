import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";

describe("Android production domain association", () => {
  it("authorizes the signed Fitician production app to handle verified links", () => {
    const statements: unknown = JSON.parse(
      readFileSync("public/.well-known/assetlinks.json", "utf8"),
    );
    expect(statements).toEqual([
      {
        relation: ["delegate_permission/common.handle_all_urls"],
        target: {
          namespace: "android_app",
          package_name: "com.fitician.app",
          sha256_cert_fingerprints: [
            "71:E0:88:FE:B1:76:7F:45:D9:E9:07:FF:34:84:AE:64:11:E5:57:D3:62:3D:F8:8D:84:3C:DF:96:42:65:56:2C",
          ],
        },
      },
    ]);
  });
});
