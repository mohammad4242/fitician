/** Never return messages, URLs, paths, functions, or raw stacks. */
export const CLIENT_EXCEPTION_TYPES = new Set([
  "Error", "TypeError", "ReferenceError", "RangeError", "SyntaxError", "URIError",
  "EvalError", "AggregateError", "InvariantViolation",
]);
export const CLIENT_SOURCE_PATTERN = /^(?:[A-Za-z][A-Za-z0-9]{0,60}-[A-Za-z0-9_-]{6,16}\.js|index\.(?:android|ios)\.bundle|main\.jsbundle):[0-9]{1,7}:[0-9]{1,7}$/u;
const FRAME = /((?:[A-Za-z][A-Za-z0-9]{0,60}-[A-Za-z0-9_-]{6,16}\.js|index\.(?:android|ios)\.bundle|main\.jsbundle):[0-9]{1,7}:[0-9]{1,7})(?:\)|\s|$)/u;

export function safeClientException(error: unknown): {
  readonly exception_type?: string;
  readonly source_location?: string;
} {
  try {
    if (!(error instanceof Error)) return {};
    const exception_type = CLIENT_EXCEPTION_TYPES.has(error.name) ? error.name : "Error";
    const stack = typeof error.stack === "string" ? error.stack.slice(0, 8192) : "";
    for (const line of stack.split("\n").slice(1, 21)) {
      const source_location = FRAME.exec(line.slice(0, 512))?.[1];
      if (source_location && CLIENT_SOURCE_PATTERN.test(source_location)) return { exception_type, source_location };
    }
    return { exception_type };
  } catch { return {}; }
}
