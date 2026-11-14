/** Isolated release verification only. No public route or production trigger imports this module. */
export function raiseSyntheticWebFailure(): never {
  throw new Error("DIAGNOSTIC_SYNTHETIC_FAILURE");
}
