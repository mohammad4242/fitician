const PUBLIC_PREFIX = "public/";

function validatePublicKey(objectKey: string): string {
  if (
    !objectKey.startsWith(PUBLIC_PREFIX) ||
    objectKey.includes("\\") ||
    objectKey.includes("//") ||
    objectKey.split("/").some((segment) => !segment || segment === "." || segment === "..")
  ) {
    throw new Error("Invalid public media object key");
  }
  return objectKey;
}

export function publicMediaUrl(objectKey: string): string {
  const key = validatePublicKey(objectKey);
  const base = import.meta.env.VITE_MEDIA_PUBLIC_BASE_URL?.trim().replace(/\/+$/, "");
  if (base) return `${base}/${key}`;
  return `/media/${key.slice(PUBLIC_PREFIX.length)}`;
}
