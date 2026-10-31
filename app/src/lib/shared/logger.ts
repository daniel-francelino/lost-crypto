const REDACTED = "[redacted]";
const SENSITIVE_KEY = /token|secret|password|api[_-]?key|authorization|cookie|confirmation/i;

export const redact = (value: unknown): unknown => {
  if (Array.isArray(value)) return value.map(redact);
  if (typeof value !== "object" || value === null) return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      SENSITIVE_KEY.test(key) ? REDACTED : redact(item),
    ]),
  );
};

export const logError = (message: string, context?: Record<string, unknown>) => {
  // eslint-disable-next-line no-console -- the single place that writes to the console
  console.error(message, context === undefined ? "" : redact(context));
};
