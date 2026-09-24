import { expect, it } from "vitest";

import { mobileRuntimeConfigFromExtra } from "./runtimeConfig";

it("normalizes the native API, trusted web origin, and optional Google client config", () => {
  expect(
    mobileRuntimeConfigFromExtra({
      environment: "preview",
      apiBaseUrl: "https://api.fitician.example/",
      frontendOrigin: "https://fitician.example/",
      publicMediaBaseUrl: "https://media.fitician.example///",
      googleAndroidClientId: "android-client.apps.googleusercontent.com",
      googleIosClientId: "ios-client.apps.googleusercontent.com",
      googleWebClientId: "web-client.apps.googleusercontent.com",
    }),
  ).toEqual({
    appLinkHost: "fitician.fit",
    apiBaseUrl: "https://api.fitician.example",
    environment: "preview",
    frontendOrigin: "https://fitician.example",
    publicMediaBaseUrl: "https://media.fitician.example",
    googleAndroidClientId: "android-client.apps.googleusercontent.com",
    googleIosClientId: "ios-client.apps.googleusercontent.com",
    googleWebClientId: "web-client.apps.googleusercontent.com",
  });
});

it("uses the safe public origin when development configuration is absent", () => {
  expect(mobileRuntimeConfigFromExtra({})).toEqual({
    appLinkHost: "fitician.fit",
    apiBaseUrl: "https://fitician.fit",
    environment: "development",
    frontendOrigin: "https://fitician.fit",
    publicMediaBaseUrl: null,
    googleAndroidClientId: null,
    googleIosClientId: null,
    googleWebClientId: null,
  });
});

it("fails closed to release semantics for an invalid explicit environment", () => {
  expect(() => mobileRuntimeConfigFromExtra({ environment: "unexpected" })).toThrow(/production/u);
});
