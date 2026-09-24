import { resolveBackendResourceUrl } from "./backendResourceUrl";

export interface PublicMediaUrlConfig {
  readonly apiBaseUrl: string;
  readonly publicMediaBaseUrl: string | null;
}

function validatePathSegments(path: string): void {
  if (!path || path.includes("\\") || /%5c/iu.test(path) || path.includes("?") || path.includes("#")) {
    throw new Error("Invalid public media path");
  }
  for (const segment of path.split("/")) {
    let decodedSegment: string;
    try {
      decodedSegment = decodeURIComponent(segment);
    } catch {
      throw new Error("Invalid public media path");
    }
    if (
      segment === ""
      || decodedSegment === "."
      || decodedSegment === ".."
      || decodedSegment.includes("/")
      || decodedSegment.includes("\\")
      || /%(?:2e|2f|5c)/iu.test(decodedSegment)
    ) {
      throw new Error("Invalid public media path");
    }
  }
}

function managedRelativePath(path: string): { readonly backendPath: string; readonly key: string } {
  if (path.startsWith("/media/")) {
    const relative = path.slice("/media/".length);
    validatePathSegments(relative);
    return { backendPath: path, key: `public/${relative}` };
  }
  if (path.startsWith("/exercises/")) {
    const relative = path.slice("/exercises/".length);
    validatePathSegments(relative);
    return { backendPath: path, key: `public/exercises/${relative}` };
  }
  throw new Error("Unsupported public media path");
}

function parsedTrustedBase(value: string, label: string): URL {
  let parsed: URL;
  try {
    parsed = new URL(value.trim());
  } catch {
    throw new Error(`${label} is invalid`);
  }
  if (
    (parsed.protocol !== "http:" && parsed.protocol !== "https:")
    || !parsed.hostname
    || parsed.username
    || parsed.password
    || parsed.search
    || parsed.hash
  ) {
    throw new Error(`${label} is invalid`);
  }
  return parsed;
}

function absolutePathFromRawUrl(value: string): string {
  const authorityStart = value.indexOf("://") + 3;
  const pathStart = value.indexOf("/", authorityStart);
  if (pathStart < 0) return "";
  const tail = value.slice(pathStart);
  const queryIndex = tail.indexOf("?");
  const hashIndex = tail.indexOf("#");
  const endIndex = [queryIndex, hashIndex].filter((index) => index >= 0).sort((a, b) => a - b)[0];
  return endIndex === undefined ? tail : tail.slice(0, endIndex);
}

function isUnderPublicBase(url: URL, base: URL): boolean {
  const basePath = base.pathname.replace(/\/+$/u, "");
  const publicPrefix = `${basePath}/public/` || "/public/";
  if (!url.pathname.startsWith(publicPrefix)) return false;
  const objectKey = url.pathname.slice(publicPrefix.length);
  try {
    validatePathSegments(objectKey);
    return objectKey.length > 0;
  } catch {
    return false;
  }
}

export function resolvePublicMediaUrl(path: string, config: PublicMediaUrlConfig): string {
  const normalizedPath = path.trim();
  if (!normalizedPath || normalizedPath !== path || normalizedPath.startsWith("//")) {
    throw new Error("Invalid public media path");
  }

  if (/^https?:\/\//iu.test(normalizedPath)) {
    const rawPath = absolutePathFromRawUrl(normalizedPath);
    if (rawPath.includes("\\")) throw new Error("Invalid public media path");
    const absoluteUrl = parsedTrustedBase(normalizedPath, "Public media URL");
    validatePathSegments(rawPath.replace(/^\//u, ""));

    if (config.publicMediaBaseUrl) {
      const publicBase = parsedTrustedBase(config.publicMediaBaseUrl, "Public media base URL");
      if (absoluteUrl.origin === publicBase.origin && isUnderPublicBase(absoluteUrl, publicBase)) {
        return absoluteUrl.toString();
      }
    }
    if (
      absoluteUrl.pathname.startsWith("/media/")
      || absoluteUrl.pathname.startsWith("/exercises/")
    ) {
      return resolveBackendResourceUrl(normalizedPath, config.apiBaseUrl);
    }
    throw new Error("Public media URL must use a configured trusted origin");
  }

  if (normalizedPath.startsWith("/") && /^[a-z][a-z\d+.-]*:/iu.test(normalizedPath)) {
    throw new Error("Unsupported public media URL scheme");
  }
  const managed = managedRelativePath(normalizedPath);
  if (!config.publicMediaBaseUrl) {
    return resolveBackendResourceUrl(managed.backendPath, config.apiBaseUrl);
  }
  parsedTrustedBase(config.publicMediaBaseUrl, "Public media base URL");
  const normalizedBase = config.publicMediaBaseUrl.trim().replace(/\/+$/u, "");
  return `${normalizedBase}/${managed.key}`;
}
