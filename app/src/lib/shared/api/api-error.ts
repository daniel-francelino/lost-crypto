export const ApiErrorKind = {
  Http: "http",
  Network: "network",
  InvalidResponse: "invalid-response",
} as const;
export type ApiErrorKind = (typeof ApiErrorKind)[keyof typeof ApiErrorKind];

export const HttpStatus = {
  Unauthorized: 401,
  Forbidden: 403,
  NotFound: 404,
  Conflict: 409,
  Unprocessable: 422,
  Unavailable: 503,
} as const;

type ValidationItem = { loc?: unknown; msg?: unknown };

const fieldOf = (loc: unknown): string => {
  if (!Array.isArray(loc)) return "";
  const last = loc.filter((part) => typeof part === "string").at(-1);
  return typeof last === "string" ? last : "";
};

const readDetail = (body: unknown): { detail: string; fieldErrors: Record<string, string> } => {
  const raw =
    typeof body === "object" && body !== null ? (body as { detail?: unknown }).detail : null;
  if (typeof raw === "string") return { detail: raw, fieldErrors: {} };
  if (!Array.isArray(raw)) return { detail: "", fieldErrors: {} };
  const fieldErrors: Record<string, string> = {};
  for (const item of raw as ValidationItem[]) {
    const field = fieldOf(item.loc);
    if (field !== "" && typeof item.msg === "string") fieldErrors[field] ??= item.msg;
  }
  return { detail: Object.values(fieldErrors)[0] ?? "", fieldErrors };
};

export class ApiError extends Error {
  readonly kind: ApiErrorKind;
  readonly status: number;
  readonly detail: string;
  readonly fieldErrors: Record<string, string>;

  constructor(
    kind: ApiErrorKind,
    status: number,
    detail: string,
    fieldErrors: Record<string, string> = {},
  ) {
    super(detail === "" ? `${kind} ${status}` : detail);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
    this.detail = detail;
    this.fieldErrors = fieldErrors;
  }

  static fromBody(status: number, body: unknown): ApiError {
    const { detail, fieldErrors } = readDetail(body);
    return new ApiError(ApiErrorKind.Http, status, detail, fieldErrors);
  }

  static network(): ApiError {
    return new ApiError(ApiErrorKind.Network, 0, "");
  }

  static invalidResponse(path: string): ApiError {
    return new ApiError(ApiErrorKind.InvalidResponse, 0, `unexpected response from ${path}`);
  }

  get isNetwork(): boolean {
    return this.kind === ApiErrorKind.Network;
  }

  hasStatus(status: number): boolean {
    return this.kind === ApiErrorKind.Http && this.status === status;
  }
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;
