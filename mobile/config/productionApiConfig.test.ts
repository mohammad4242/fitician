import { expect, it } from "vitest";

import {
  PRODUCTION_API_BASE_URL,
  PRODUCTION_FRONTEND_ORIGIN,
  resolveApiBaseUrl,
  resolveFrontendOrigin,
} from "./productionApiConfig";

it("accepts only the approved public HTTPS origin for production", () => {
  expect(PRODUCTION_API_BASE_URL).toBe("https://fitician.fit");
  expect(resolveApiBaseUrl(PRODUCTION_API_BASE_URL, "production")).toBe(
    PRODUCTION_API_BASE_URL,
  );
  expect(() => resolveApiBaseUrl(undefined, "production")).toThrow(/required/u);
  for (const rejected of [
    "http://fitician.fit",
    "https://api.fitician.example",
    "http://localhost:8001",
    "http://127.0.0.1:8001",
    "http://10.0.2.2:8001",
    "http://192.168.1.107:8001",
    "http://100.97.78.5:8001",
    "https://backend.local",
  ]) {
    expect(() => resolveApiBaseUrl(rejected, "production")).toThrow(
      /approved production origin/u,
    );
  }
});

it("requires the configured trusted origin for production", () => {
  expect(PRODUCTION_FRONTEND_ORIGIN).toBe("https://fitician.fit");
  expect(resolveFrontendOrigin(PRODUCTION_FRONTEND_ORIGIN, "production")).toBe(
    PRODUCTION_FRONTEND_ORIGIN,
  );
  expect(() => resolveFrontendOrigin(undefined, "production")).toThrow(/required/u);
  expect(() => resolveFrontendOrigin("https://fitician.fit/api", "production")).toThrow(
    /approved production origin/u,
  );
});

it("keeps development configuration explicit while allowing local development targets", () => {
  expect(resolveApiBaseUrl("http://10.0.2.2:8001", "development")).toBe(
    "http://10.0.2.2:8001",
  );
  expect(resolveFrontendOrigin("http://localhost:5173", "development")).toBe(
    "http://localhost:5173",
  );
});

it("uses the safe public origin when development configuration is missing", () => {
  expect(resolveApiBaseUrl(undefined, "development")).toBe(PRODUCTION_API_BASE_URL);
  expect(resolveFrontendOrigin(undefined, "development")).toBe(PRODUCTION_FRONTEND_ORIGIN);
});
