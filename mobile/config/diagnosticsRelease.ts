export function diagnosticsRelease(commit: unknown, nativeBuild?: unknown): {
  commit?: string;
  release?: string;
  dist?: string;
} {
  const known = typeof commit === "string" && /^[a-f0-9]{40}$/u.test(commit);
  const dist = typeof nativeBuild === "string" && /^[0-9][0-9A-Za-z_.-]{0,63}$/u.test(nativeBuild)
    ? nativeBuild : undefined;
  return {
    ...(known ? { commit, release: `fitician-mobile@${commit}` } : {}),
    ...(dist ? { dist } : {}),
  };
}
