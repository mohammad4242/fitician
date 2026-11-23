/** Rebuild SDK envelopes from permitted technical evidence, never arbitrary application text. */
export function sanitizeSentryEvent<T extends object>(event: T): T {
  const input = event as Record<string, unknown>;
  const output: Record<string, unknown> = {};
  for (const key of ["event_id", "timestamp", "platform", "level", "release", "environment", "dist", "sdk", "type", "start_timestamp"]) {
    if (input[key] !== undefined) output[key] = input[key];
  }
  const token = (value: unknown) => typeof value === "string" && /^[A-Za-z0-9_.:@/-]{1,160}$/.test(value) ? value : undefined;
  const record = (value: unknown): Record<string, unknown> => value && typeof value === "object" ? value as Record<string, unknown> : {};
  const array = (value: unknown): unknown[] => Array.isArray(value) ? value : [];
  const sourcePath = (value: unknown): string | undefined => {
    if (typeof value !== "string") return undefined;
    const path = value.replaceAll("\\", "/").split(/[?#]/)[0];
    const match = path.match(/(?:^|\/)((?:src|app|platform|assets)\/[^?#]+)$/);
    if (match && /^[A-Za-z0-9_./-]+$/.test(match[1]) && !match[1].split("/").includes("..")) return match[1].slice(0, 240);
    const base = path.split("/").pop();
    return base && /^[A-Za-z0-9_.-]{1,160}$/.test(base) ? base : undefined;
  };
  const values = array(record(input.exception).values).slice(0, 16).map(value => {
    const exception = record(value);
    const frames = array(record(exception.stacktrace).frames).slice(-100).map(value => {
      const frame = record(value);
      const filename = String(frame.filename ?? "").replaceAll("\\", "/");
      // Keep emitted bundle URLs without origin/query for Debug-ID source mapping.
      const path = sourcePath(filename);
      return {
        ...(path ? { filename: path } : {}),
        ...(path && filename.includes("://") ? { abs_path: path } : {}),
        ...(sourcePath(frame.package) ? { package: sourcePath(frame.package) } : {}),
        ...(token(frame.instruction_addr) ? { instruction_addr: token(frame.instruction_addr) } : {}),
        ...(token(frame.function) ? { function: token(frame.function) } : {}),
        ...(Number.isInteger(frame.lineno) ? { lineno: frame.lineno } : {}),
        ...(Number.isInteger(frame.colno) ? { colno: frame.colno } : {}),
      };
    });
    return { type: token(exception.type) ?? "Error", value: "[redacted]", stacktrace: { frames } };
  });
  if (values.length) output.exception = { values };
  const trace = record(record(input.contexts).trace);
  const safeTrace: Record<string, unknown> = {};
  for (const key of ["trace_id", "span_id", "parent_span_id", "status"]) {
    if (token(trace[key])) safeTrace[key] = trace[key];
  }
  if (Object.keys(safeTrace).length) output.contexts = { trace: safeTrace };
  const componentStack = record(record(input.contexts).react).componentStack;
  if (typeof componentStack === "string") {
    const components = componentStack.split("\n").slice(0, 50).flatMap(line => {
      const match = line.match(/^\s+(?:at|in)\s+([A-Za-z_$][A-Za-z0-9_$.<>-]{0,100})(?:\s|$)/);
      return match ? [match[1]] : [];
    });
    if (components.length) output.contexts = { ...record(output.contexts), react: { components } };
  }
  const tags = record(input.tags);
  output.tags = Object.fromEntries(["service", "diagnostic_event_id", "request_id", "operation_id", "job_id", "stage", "error_code"].filter(key => token(tags[key])).map(key => [key, tags[key]]));
  if (input.type === "transaction") { output.transaction = "request"; output.spans = []; }
  const images = array(record(input.debug_meta).images).map(value => {
    const image = record(value);
    return { ...Object.fromEntries(["type", "debug_id", "code_id", "image_addr", "image_size", "arch"].filter(key => typeof image[key] === "number" || token(image[key])).map(key => [key, image[key]])), ...(sourcePath(image.code_file) ? { code_file: sourcePath(image.code_file) } : {}) };
  });
  if (images.length) output.debug_meta = { images };
  return output as T;
}
