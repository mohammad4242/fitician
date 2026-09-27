import { expect, it, vi } from "vitest";

import {
  ApiError,
  type BinaryDownload,
  type MobileAuthTokens,
  type TransportRequest,
} from "@fitician/core";

import { MobileAuthClient } from "./authClient";

function deferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function tokensFor(userId: string, accessToken: string, refreshToken: string): MobileAuthTokens {
  return {
    access_token: accessToken,
    expires_in: 900,
    refresh_expires_in: 2_592_000,
    refresh_token: refreshToken,
    token_type: "Bearer",
    user: {
      created_at: "2026-01-01T00:00:00Z",
      email: `${userId}@example.com`,
      id: userId,
      is_admin: false,
      phone_number: null,
    },
  };
}

vi.mock("expo-secure-store", () => ({
  deleteItemAsync: vi.fn(),
  getItemAsync: vi.fn(),
  setItemAsync: vi.fn(),
}));

it("refreshes concurrent unauthorized requests through one refresh call", async () => {
  let refreshCalls = 0;

  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => undefined,
      read: async () => "refresh-token",
      write: async () => undefined,
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshCalls += 1;
          return {
            access_token: "refreshed-access",
            expires_in: 900,
            refresh_expires_in: 2_592_000,
            refresh_token: "rotated-refresh",
            token_type: "Bearer" as const,
            user: {
              created_at: "2026-01-01T00:00:00Z",
              email: "member@example.com",
              id: "member-1",
              is_admin: false,
              phone_number: null,
            },
          } as TResponse;
        }
        if (request.headers?.Authorization === "Bearer refreshed-access") {
          return { ok: true } as TResponse;
        }
        throw new ApiError(401, "Authentication required");
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  const [first, second] = await Promise.all([
    client.request<{ ok: boolean }>({ path: "/api/v1/member", method: "GET" }),
    client.request<{ ok: boolean }>({ path: "/api/v1/member", method: "GET" }),
  ]);

  expect(first).toEqual(second);
  expect(first).toEqual({ ok: true });
  expect(refreshCalls).toBe(1);
});

it("refreshes inside the configured clock-skew window", async () => {
  let now = 1_000;
  let refreshCalls = 0;
  let staleAccessCalls = 0;
  let storedRefreshToken: string | null = "initial-refresh";
  const client = new MobileAuthClient({
    now: () => now,
    clockSkewMilliseconds: 30_000,
    refreshTokenStorage: {
      clear: async () => {
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshCalls += 1;
          return {
            access_token: "fresh-access",
            expires_in: 900,
            refresh_expires_in: 2_592_000,
            refresh_token: "fresh-refresh",
            token_type: "Bearer" as const,
            user: {
              created_at: "2026-01-01T00:00:00Z",
              email: "member@example.com",
              id: "member-1",
              is_admin: false,
              phone_number: null,
            },
          } as TResponse;
        }
        if (request.headers?.Authorization === "Bearer fresh-access") {
          return { ok: true } as TResponse;
        }
        staleAccessCalls += 1;
        throw new ApiError(401, "Authentication required");
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession({
    access_token: "soon-expired-access",
    expires_in: 20,
    refresh_expires_in: 2_592_000,
    refresh_token: "initial-refresh",
    token_type: "Bearer",
    user: {
      created_at: "2026-01-01T00:00:00Z",
      email: "member@example.com",
      id: "member-1",
      is_admin: false,
      phone_number: null,
    },
  });
  now += 1;

  await expect(client.request<{ ok: boolean }>({ path: "/api/v1/member", method: "GET" })).resolves
    .toEqual({ ok: true });
  expect(refreshCalls).toBe(1);
  expect(staleAccessCalls).toBe(0);
});

it("clears a revoked session and notifies once", async () => {
  let clearCalls = 0;
  let expiryNotifications = 0;
  const client = new MobileAuthClient({
    onSessionExpired: () => {
      expiryNotifications += 1;
    },
    refreshTokenStorage: {
      clear: async () => {
        clearCalls += 1;
      },
      read: async () => "revoked-refresh",
      write: async () => undefined,
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(): Promise<TResponse> => {
        throw new ApiError(401, "Refresh token is invalid");
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await expect(client.restoreSession()).resolves.toBe(false);
  expect(clearCalls).toBe(1);
  expect(expiryNotifications).toBe(1);
});

it("retries one unauthorized request and expires after a second 401", async () => {
  let refreshCalls = 0;
  let clearCalls = 0;
  let expiryNotifications = 0;
  let storedRefreshToken: string | null = "initial-refresh";
  const client = new MobileAuthClient({
    onSessionExpired: () => {
      expiryNotifications += 1;
    },
    refreshTokenStorage: {
      clear: async () => {
        clearCalls += 1;
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshCalls += 1;
          return {
            access_token: "fresh-access",
            expires_in: 900,
            refresh_expires_in: 2_592_000,
            refresh_token: "fresh-refresh",
            token_type: "Bearer" as const,
            user: {
              created_at: "2026-01-01T00:00:00Z",
              email: "member@example.com",
              id: "member-1",
              is_admin: false,
              phone_number: null,
            },
          } as TResponse;
        }
        throw new ApiError(401, "Authentication required");
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession({
    access_token: "initial-access",
    expires_in: 900,
    refresh_expires_in: 2_592_000,
    refresh_token: "initial-refresh",
    token_type: "Bearer",
    user: {
      created_at: "2026-01-01T00:00:00Z",
      email: "member@example.com",
      id: "member-1",
      is_admin: false,
      phone_number: null,
    },
  });

  await expect(client.request({ path: "/api/v1/member", method: "GET" })).rejects.toMatchObject({
    status: 401,
  });
  expect(refreshCalls).toBe(1);
  expect(clearCalls).toBe(1);
  expect(expiryNotifications).toBe(1);
});

it("does not repeat a rejected refresh during one request", async () => {
  let refreshCalls = 0;
  let clearCalls = 0;
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => {
        clearCalls += 1;
      },
      read: async () => "revoked-refresh",
      write: async () => undefined,
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshCalls += 1;
          throw new ApiError(401, "Refresh token is invalid");
        }
        throw new ApiError(401, "Authentication required");
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await expect(client.request({ path: "/api/v1/member", method: "GET" })).rejects.toMatchObject({
    status: 401,
  });
  expect(refreshCalls).toBe(1);
  expect(clearCalls).toBe(1);
});

it("authenticates binary downloads and refreshes once after a 401", async () => {
  let refreshCalls = 0;
  let downloadCalls = 0;
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => undefined,
      read: async () => "initial-refresh",
      write: async () => undefined,
    },
    transport: {
      download: async (request): Promise<BinaryDownload> => {
        downloadCalls += 1;
        if (request.headers?.Authorization !== "Bearer fresh-access") {
          throw new ApiError(401, "Authentication required");
        }
        return { bytes: Uint8Array.from([1, 2]), contentType: "image/jpeg", filename: "photo.jpg" };
      },
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshCalls += 1;
          return {
            access_token: "fresh-access",
            expires_in: 900,
            refresh_expires_in: 2_592_000,
            refresh_token: "fresh-refresh",
            token_type: "Bearer" as const,
            user: {
              created_at: "2026-01-01T00:00:00Z",
              email: "member@example.com",
              id: "member-1",
              is_admin: false,
              phone_number: null,
            },
          } as TResponse;
        }
        return {} as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession({
    access_token: "stale-access",
    expires_in: 900,
    refresh_expires_in: 2_592_000,
    refresh_token: "initial-refresh",
    token_type: "Bearer",
    user: {
      created_at: "2026-01-01T00:00:00Z",
      email: "member@example.com",
      id: "member-1",
      is_admin: false,
      phone_number: null,
    },
  });

  await expect(
    client.download({
      method: "GET",
      path: "/api/v1/profile/photo/member-1",
      responseType: "binary",
    }),
  ).resolves.toEqual({
    bytes: Uint8Array.from([1, 2]),
    contentType: "image/jpeg",
    filename: "photo.jpg",
  });
  expect(downloadCalls).toBe(2);
  expect(refreshCalls).toBe(1);
});

it("does not replay a stale mutation with the next user's credentials", async () => {
  const firstMutationStarted = deferred<string | null>();
  const firstMutationResponse = deferred<{ ok: boolean }>();
  const mutationAuthorizations: Array<string | null> = [];
  let refreshCalls = 0;
  let refreshReads = 0;
  let storedRefreshToken: string | null = null;
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => {
        storedRefreshToken = null;
      },
      read: async () => {
        refreshReads += 1;
        return storedRefreshToken;
      },
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshCalls += 1;
          throw new Error("A stale mutation must not start a refresh");
        }
        mutationAuthorizations.push(request.headers?.Authorization ?? null);
        if (mutationAuthorizations.length === 1) {
          firstMutationStarted.resolve(request.headers?.Authorization ?? null);
          return firstMutationResponse.promise as Promise<TResponse>;
        }
        return { ok: true } as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession(tokensFor("user-a", "access-a", "refresh-a"));
  const staleMutation = client.request<{ ok: boolean }>({
    path: "/api/v1/profile",
    method: "PATCH",
    body: { display_name: "A's change" },
  });
  await expect(firstMutationStarted.promise).resolves.toBe("Bearer access-a");

  await client.clearSession();
  await client.setSession(tokensFor("user-b", "access-b", "refresh-b"));
  firstMutationResponse.reject(new ApiError(401, "Authentication required"));

  await expect(staleMutation).rejects.toMatchObject({ status: 401 });
  expect(mutationAuthorizations).toEqual(["Bearer access-a"]);
  expect(refreshCalls).toBe(0);
  expect(refreshReads).toBe(0);
  expect(client.getUser()?.id).toBe("user-b");
  expect(storedRefreshToken).toBe("refresh-b");
});

it("discards an old refresh response after a newer user signs in", async () => {
  const refreshStarted = deferred<string | undefined>();
  const refreshResponse = deferred<MobileAuthTokens>();
  const businessAuthorizations: Array<string | null> = [];
  let storedRefreshToken: string | null = null;
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => {
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshStarted.resolve((request.body as { refresh_token?: string }).refresh_token);
          return refreshResponse.promise as Promise<TResponse>;
        }
        businessAuthorizations.push(request.headers?.Authorization ?? null);
        if (request.path === "/api/v1/profile") {
          throw new ApiError(401, "Authentication required");
        }
        return { ok: true } as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession(tokensFor("user-a", "access-a", "refresh-a"));
  const staleMutation = client.request<{ ok: boolean }>({
    path: "/api/v1/profile",
    method: "PATCH",
    body: { display_name: "A's change" },
  });
  await expect(refreshStarted.promise).resolves.toBe("refresh-a");

  await client.clearSession();
  await client.setSession(tokensFor("user-b", "access-b", "refresh-b"));
  refreshResponse.resolve(tokensFor("user-a", "refreshed-access-a", "rotated-refresh-a"));

  await expect(staleMutation).rejects.toMatchObject({ status: 401 });
  expect(businessAuthorizations).toEqual(["Bearer access-a"]);
  expect(client.getUser()?.id).toBe("user-b");
  expect(storedRefreshToken).toBe("refresh-b");
  await expect(client.request({ path: "/api/v1/profile/current", method: "GET" })).resolves
    .toEqual({ ok: true });
  expect(businessAuthorizations.at(-1)).toBe("Bearer access-b");
  expect(storedRefreshToken).toBe("refresh-b");
});

it("does not send an initially unauthenticated request after its session becomes stale", async () => {
  const refreshStarted = deferred<string | undefined>();
  const refreshResponse = deferred<MobileAuthTokens>();
  const businessAuthorizations: Array<string | null> = [];
  let storedRefreshToken: string | null = "refresh-a";
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => {
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshStarted.resolve((request.body as { refresh_token?: string }).refresh_token);
          return refreshResponse.promise as Promise<TResponse>;
        }
        businessAuthorizations.push(request.headers?.Authorization ?? null);
        return { ok: true } as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  const staleRequest = client.request({ path: "/api/v1/member", method: "GET" });
  await expect(refreshStarted.promise).resolves.toBe("refresh-a");
  await client.clearSession();
  await client.setSession(tokensFor("user-b", "access-b", "refresh-b"));
  refreshResponse.resolve(tokensFor("user-a", "refreshed-access-a", "rotated-refresh-a"));

  await expect(staleRequest).rejects.toMatchObject({ status: 401 });
  expect(businessAuthorizations).toEqual([]);
  expect(client.getUser()?.id).toBe("user-b");
  expect(storedRefreshToken).toBe("refresh-b");
});

it("keeps restore signed in when an older refresh finishes after a new login", async () => {
  const refreshStarted = deferred<string | undefined>();
  const refreshResponse = deferred<MobileAuthTokens>();
  let storedRefreshToken: string | null = "refresh-a";
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => {
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshStarted.resolve((request.body as { refresh_token?: string }).refresh_token);
          return refreshResponse.promise as Promise<TResponse>;
        }
        return {} as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  const restoring = client.restoreSession();
  await expect(refreshStarted.promise).resolves.toBe("refresh-a");
  await client.setSession(tokensFor("user-b", "access-b", "refresh-b"));
  refreshResponse.resolve(tokensFor("user-a", "refreshed-access-a", "rotated-refresh-a"));

  await expect(restoring).resolves.toBe(true);
  expect(client.getUser()?.id).toBe("user-b");
  expect(storedRefreshToken).toBe("refresh-b");
});

it("does not expire a newer session after a stale retry receives a second 401", async () => {
  const retryStarted = deferred<string | null>();
  const retryResponse = deferred<{ ok: boolean }>();
  const businessAuthorizations: Array<string | null> = [];
  let expiryNotifications = 0;
  let storedRefreshToken: string | null = null;
  let clearCalls = 0;
  let mutationCalls = 0;
  const client = new MobileAuthClient({
    onSessionExpired: () => {
      expiryNotifications += 1;
    },
    refreshTokenStorage: {
      clear: async () => {
        clearCalls += 1;
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          return tokensFor("user-a", "refreshed-access-a", "rotated-refresh-a") as TResponse;
        }
        businessAuthorizations.push(request.headers?.Authorization ?? null);
        if (request.path === "/api/v1/profile") {
          mutationCalls += 1;
          if (mutationCalls === 1) {
            throw new ApiError(401, "Authentication required");
          }
          retryStarted.resolve(request.headers?.Authorization ?? null);
          return retryResponse.promise as Promise<TResponse>;
        }
        return { ok: true } as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession(tokensFor("user-a", "access-a", "refresh-a"));
  const staleMutation = client.request<{ ok: boolean }>({
    path: "/api/v1/profile",
    method: "PATCH",
    body: { display_name: "A's change" },
  });
  await expect(retryStarted.promise).resolves.toBe("Bearer refreshed-access-a");

  await client.clearSession();
  await client.setSession(tokensFor("user-b", "access-b", "refresh-b"));
  retryResponse.reject(new ApiError(401, "Authentication required"));

  await expect(staleMutation).rejects.toMatchObject({ status: 401 });
  expect(client.getUser()?.id).toBe("user-b");
  expect(storedRefreshToken).toBe("refresh-b");
  expect(expiryNotifications).toBe(0);
  expect(clearCalls).toBe(1);
  await expect(client.request({ path: "/api/v1/profile/current", method: "GET" })).resolves
    .toEqual({ ok: true });
  expect(businessAuthorizations.at(-1)).toBe("Bearer access-b");
});

it("serializes delayed refresh-token writes ahead of newer session storage", async () => {
  const refreshWriteStarted = deferred<void>();
  const finishRefreshWrite = deferred<void>();
  const refreshStarted = deferred<void>();
  const businessCalls: string[] = [];
  let storedRefreshToken: string | null = null;
  const client = new MobileAuthClient({
    refreshTokenStorage: {
      clear: async () => {
        storedRefreshToken = null;
      },
      read: async () => storedRefreshToken,
      write: async (token) => {
        if (token === "rotated-refresh-a") {
          refreshWriteStarted.resolve();
          await finishRefreshWrite.promise;
        }
        storedRefreshToken = token;
      },
    },
    transport: {
      download: async () => ({ bytes: new Uint8Array(), contentType: null, filename: null }),
      request: async <TResponse>(request: TransportRequest): Promise<TResponse> => {
        if (request.path.endsWith("/refresh")) {
          refreshStarted.resolve();
          return tokensFor("user-a", "refreshed-access-a", "rotated-refresh-a") as TResponse;
        }
        businessCalls.push(request.headers?.Authorization ?? "none");
        if (request.path === "/api/v1/profile") {
          throw new ApiError(401, "Authentication required");
        }
        return { ok: true } as TResponse;
      },
      upload: async <TResponse>(): Promise<TResponse> => ({ ok: true }) as TResponse,
    },
  });

  await client.setSession(tokensFor("user-a", "access-a", "refresh-a"));
  const staleMutation = client.request({ path: "/api/v1/profile", method: "PATCH" });
  await refreshStarted.promise;
  await refreshWriteStarted.promise;

  const clearOldSession = client.clearSession();
  const adoptNewSession = client.setSession(tokensFor("user-b", "access-b", "refresh-b"));
  finishRefreshWrite.resolve();
  await Promise.all([clearOldSession, adoptNewSession]);
  await expect(staleMutation).rejects.toMatchObject({ status: 401 });

  expect(client.getUser()?.id).toBe("user-b");
  expect(storedRefreshToken).toBe("refresh-b");
  await expect(client.request({ path: "/api/v1/profile/current", method: "GET" })).resolves
    .toEqual({ ok: true });
  expect(businessCalls.at(-1)).toBe("Bearer access-b");
});
