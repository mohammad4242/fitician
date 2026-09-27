import {
  ApiError,
  type BinaryDownload,
  type BinaryDownloadRequest,
  type FiticianTransport,
  type MobileAuthTokens,
  type MultipartUploadRequest,
  type RefreshTokenStorage,
  type TransportRequest,
} from "@fitician/core";
import type { User } from "@fitician/core/auth";

import { MemoryAccessTokenStore } from "./tokenStore";

const DEFAULT_CLOCK_SKEW_MILLISECONDS = 30_000;
const DEFAULT_REFRESH_PATH = "/api/v1/auth/mobile/refresh";

type RefreshOutcome = "refreshed" | "missing" | "rejected" | "stale";

interface GenerationFlight<T> {
  generation: number;
  promise: Promise<T>;
}

export interface MobileAuthClientOptions {
  transport: FiticianTransport;
  refreshTokenStorage: RefreshTokenStorage;
  accessTokenStore?: MemoryAccessTokenStore;
  now?: () => number;
  clockSkewMilliseconds?: number;
  refreshPath?: string;
  onSessionExpired?: () => void | Promise<void>;
}

export class MobileAuthClient {
  private readonly transport: FiticianTransport;
  private readonly refreshTokenStorage: RefreshTokenStorage;
  private readonly accessTokenStore: MemoryAccessTokenStore;
  private readonly clockSkewMilliseconds: number;
  private readonly refreshPath: string;
  private readonly onSessionExpired: (() => void | Promise<void>) | undefined;
  private refreshInFlight: GenerationFlight<RefreshOutcome> | null = null;
  private sessionExpiryInFlight: GenerationFlight<void> | null = null;
  private storageMutationTail: Promise<void> = Promise.resolve();
  private sessionGeneration = 0;
  private sessionExpiredNotified = false;
  private user: User | null = null;

  constructor(options: MobileAuthClientOptions) {
    this.transport = options.transport;
    this.refreshTokenStorage = options.refreshTokenStorage;
    this.accessTokenStore =
      options.accessTokenStore ?? new MemoryAccessTokenStore(options.now ?? Date.now);
    this.clockSkewMilliseconds =
      options.clockSkewMilliseconds ?? DEFAULT_CLOCK_SKEW_MILLISECONDS;
    this.refreshPath = options.refreshPath ?? DEFAULT_REFRESH_PATH;
    this.onSessionExpired = options.onSessionExpired;
  }

  async setSession(tokens: MobileAuthTokens): Promise<void> {
    const generation = ++this.sessionGeneration;
    this.accessTokenStore.set(tokens);
    this.user = tokens.user;
    this.sessionExpiredNotified = false;

    await this.serializeStorageOperation(async () => {
      if (generation !== this.sessionGeneration) {
        return;
      }
      try {
        await this.refreshTokenStorage.write(tokens.refresh_token);
      } catch (error) {
        if (generation !== this.sessionGeneration) {
          return;
        }
        this.sessionGeneration += 1;
        this.accessTokenStore.clear();
        this.user = null;
        try {
          await this.refreshTokenStorage.clear();
        } catch {
          // Preserve the write failure while making a best-effort cleanup.
        }
        throw error;
      }
    });
  }

  getUser(): User | null {
    return this.user;
  }

  async restoreSession(): Promise<boolean> {
    const generation = this.sessionGeneration;
    if (this.hasValidCurrentSession()) {
      return true;
    }

    const outcome = await this.refreshOnce(generation);
    if (generation !== this.sessionGeneration) {
      return this.hasValidCurrentSession();
    }
    if (outcome === "rejected") {
      await this.expireSession(generation);
      return this.hasValidCurrentSession();
    }
    if (outcome === "stale") {
      return this.hasValidCurrentSession();
    }
    return outcome === "refreshed" && this.hasValidCurrentSession();
  }

  async clearSession(): Promise<void> {
    const generation = ++this.sessionGeneration;
    this.accessTokenStore.clear();
    this.user = null;

    await this.serializeStorageOperation(async () => {
      if (generation !== this.sessionGeneration) {
        return;
      }
      await this.refreshTokenStorage.clear();
    });
  }

  async request<TResponse>(request: TransportRequest): Promise<TResponse> {
    return this.executeWithAuthentication(request, (authenticatedRequest) =>
      this.transport.request<TResponse>(authenticatedRequest),
    );
  }

  async download(request: BinaryDownloadRequest): Promise<BinaryDownload> {
    return this.executeWithAuthentication(request, (authenticatedRequest) =>
      this.transport.download(authenticatedRequest),
    );
  }

  async upload<TResponse>(request: MultipartUploadRequest): Promise<TResponse> {
    return this.executeWithAuthentication(request, (authenticatedRequest) =>
      this.transport.upload<TResponse>(authenticatedRequest),
    );
  }

  private async executeWithAuthentication<TRequest extends TransportRequest, TResponse>(
    request: TRequest,
    send: (authenticatedRequest: TRequest) => Promise<TResponse>,
  ): Promise<TResponse> {
    const generation = this.sessionGeneration;
    let accessToken = this.accessTokenStore.getValid(this.clockSkewMilliseconds);
    let initialRefreshOutcome: RefreshOutcome | null = null;

    if (accessToken === null) {
      initialRefreshOutcome = await this.refreshOnce(generation);
      if (generation !== this.sessionGeneration || initialRefreshOutcome === "stale") {
        throw this.authenticationRequired();
      }
      if (initialRefreshOutcome === "rejected") {
        await this.expireSession(generation);
        throw this.authenticationRequired();
      }
      accessToken = this.accessTokenStore.getValid(this.clockSkewMilliseconds);
    }

    if (generation !== this.sessionGeneration) {
      throw this.authenticationRequired();
    }

    try {
      return await send(this.withAccessToken(request, accessToken));
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        throw error;
      }
      if (generation !== this.sessionGeneration) {
        throw error;
      }

      if (initialRefreshOutcome !== null) {
        if (initialRefreshOutcome === "refreshed") {
          await this.expireSession(generation);
        }
        throw error;
      }

      const refreshOutcome = await this.refreshOnce(generation);
      if (generation !== this.sessionGeneration || refreshOutcome === "stale") {
        throw error;
      }
      if (refreshOutcome !== "refreshed") {
        await this.expireSession(generation);
        throw error;
      }

      const retryToken = this.accessTokenStore.getValid(this.clockSkewMilliseconds);
      if (retryToken === null || generation !== this.sessionGeneration) {
        await this.expireSession(generation);
        throw error;
      }

      try {
        return await send(this.withAccessToken(request, retryToken));
      } catch (retryError) {
        if (
          retryError instanceof ApiError &&
          retryError.status === 401 &&
          generation === this.sessionGeneration
        ) {
          await this.expireSession(generation);
        }
        throw retryError;
      }
    }
  }

  private authenticationRequired(): ApiError {
    return new ApiError(401, "Authentication required");
  }

  private hasValidCurrentSession(): boolean {
    return (
      this.user !== null &&
      this.accessTokenStore.getValid(this.clockSkewMilliseconds) !== null
    );
  }

  private withAccessToken<TRequest extends TransportRequest>(
    request: TRequest,
    accessToken: string | null,
  ): TRequest {
    if (accessToken === null) {
      return request;
    }

    return {
      ...request,
      headers: {
        ...request.headers,
        Authorization: `Bearer ${accessToken}`,
      },
    } as TRequest;
  }

  private serializeStorageOperation<T>(operation: () => Promise<T>): Promise<T> {
    const result = this.storageMutationTail.then(operation, operation);
    this.storageMutationTail = result.then(
      () => undefined,
      () => undefined,
    );
    return result;
  }

  private refreshOnce(generation: number): Promise<RefreshOutcome> {
    if (generation !== this.sessionGeneration) {
      return Promise.resolve("stale");
    }
    if (this.refreshInFlight?.generation === generation) {
      return this.refreshInFlight.promise;
    }

    const promise = this.performRefresh(generation);
    const flight = { generation, promise };
    this.refreshInFlight = flight;
    promise.then(
      () => {
        if (this.refreshInFlight === flight) {
          this.refreshInFlight = null;
        }
      },
      () => {
        if (this.refreshInFlight === flight) {
          this.refreshInFlight = null;
        }
      },
    );
    return promise;
  }

  private async performRefresh(generation: number): Promise<RefreshOutcome> {
    if (generation !== this.sessionGeneration) {
      return "stale";
    }
    await this.storageMutationTail;
    if (generation !== this.sessionGeneration) {
      return "stale";
    }
    let refreshToken: string | null;
    try {
      refreshToken = await this.refreshTokenStorage.read();
    } catch (error) {
      if (generation !== this.sessionGeneration) {
        return "stale";
      }
      throw error;
    }
    if (generation !== this.sessionGeneration) {
      return "stale";
    }
    if (refreshToken === null) {
      return "missing";
    }

    let tokens: MobileAuthTokens;
    try {
      tokens = await this.transport.request<MobileAuthTokens>({
        path: this.refreshPath,
        method: "POST",
        body: { refresh_token: refreshToken },
      });
    } catch (error) {
      if (generation !== this.sessionGeneration) {
        return "stale";
      }
      if (error instanceof ApiError && error.status === 401) {
        return "rejected";
      }
      throw error;
    }

    if (generation !== this.sessionGeneration) {
      return "stale";
    }
    const adopted = await this.adoptRefreshedTokens(generation, tokens);
    return adopted ? "refreshed" : "stale";
  }

  private async adoptRefreshedTokens(
    generation: number,
    tokens: MobileAuthTokens,
  ): Promise<boolean> {
    return this.serializeStorageOperation(async () => {
      if (generation !== this.sessionGeneration) {
        return false;
      }
      try {
        await this.refreshTokenStorage.write(tokens.refresh_token);
      } catch (error) {
        if (generation !== this.sessionGeneration) {
          return false;
        }
        throw error;
      }
      if (generation !== this.sessionGeneration) {
        return false;
      }
      this.accessTokenStore.set(tokens);
      this.user = tokens.user;
      return true;
    });
  }

  private expireSession(generation: number): Promise<void> {
    if (generation !== this.sessionGeneration) {
      return Promise.resolve();
    }
    if (this.sessionExpiryInFlight?.generation === generation) {
      return this.sessionExpiryInFlight.promise;
    }

    const expiryGeneration = ++this.sessionGeneration;
    this.accessTokenStore.clear();
    this.user = null;
    const shouldNotify = !this.sessionExpiredNotified;
    this.sessionExpiredNotified = true;
    const promise = this.serializeStorageOperation(async () => {
      if (expiryGeneration !== this.sessionGeneration) {
        return;
      }
      await this.refreshTokenStorage.clear();
      if (expiryGeneration === this.sessionGeneration && shouldNotify) {
        await this.onSessionExpired?.();
      }
    });
    const flight = { generation, promise };
    this.sessionExpiryInFlight = flight;
    promise.then(
      () => {
        if (this.sessionExpiryInFlight === flight) {
          this.sessionExpiryInFlight = null;
        }
      },
      () => {
        if (this.sessionExpiryInFlight === flight) {
          this.sessionExpiryInFlight = null;
        }
      },
    );
    return promise;
  }
}
