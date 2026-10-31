import { ApiError } from "@/lib/shared/api/api-error";
import { HttpMethod, NO_CONTENT, buildUrl, failure, readBody, send } from "@/lib/shared/api/http";
import { type User, tokenSchema } from "@/lib/shared/api/schemas";
import { addSecondsMs, nowMs } from "@/lib/shared/dates";

const RENEW_MARGIN_MS = 30_000;
const JSON_HEADERS = { "Content-Type": "application/json" };

type SessionState = { token: string; expiresAtMs: number; user: User } | null;

let state: SessionState = null;
let pendingRefresh: Promise<User | null> | null = null;
let signedOutOnPurpose = false;
const listeners = new Set<() => void>();

const publish = () => {
  for (const listener of listeners) listener();
};

export const subscribeSession = (listener: () => void): (() => void) => {
  listeners.add(listener);
  return () => listeners.delete(listener);
};

export const getSessionUser = (): User | null => state?.user ?? null;

export const getAccessToken = (): string | null => state?.token ?? null;

export const hasFreshToken = (now: number = nowMs()): boolean =>
  state !== null && state.expiresAtMs - now > RENEW_MARGIN_MS;

export const setSession = (token: string, expiresInSeconds: number, user: User): void => {
  state = { token, expiresAtMs: addSecondsMs(nowMs(), expiresInSeconds), user };
  signedOutOnPurpose = false;
  publish();
};

export const clearSession = (): void => {
  state = null;
  publish();
};

export const setSessionUser = (user: User): void => {
  if (state === null) return;
  state = { ...state, user };
  publish();
};

const authCall = async (path: string, init: RequestInit): Promise<Response> =>
  send(buildUrl(path), { ...init, credentials: "include" });

const acceptToken = async (response: Response, path: string): Promise<User> => {
  const parsed = tokenSchema.safeParse(await readBody(response));
  if (!parsed.success) throw ApiError.invalidResponse(path);
  setSession(parsed.data.access_token, parsed.data.expires_in, parsed.data.user);
  return parsed.data.user;
};

const doRefresh = async (): Promise<User | null> => {
  const path = "/auth/refresh";
  const response = await authCall(path, { method: HttpMethod.Post });
  if (response.ok) return acceptToken(response, path);
  clearSession();
  if (response.status === 401) return null;
  throw await failure(response);
};

export const refreshSession = (): Promise<User | null> => {
  pendingRefresh ??= doRefresh().finally(() => {
    pendingRefresh = null;
  });
  return pendingRefresh;
};

export const ensureSession = async (): Promise<User | null> => {
  if (hasFreshToken()) return getSessionUser();
  if (signedOutOnPurpose) return null;
  return refreshSession();
};

export const login = async (username: string, password: string): Promise<User> => {
  const path = "/auth/login";
  const response = await authCall(path, {
    method: HttpMethod.Post,
    headers: JSON_HEADERS,
    body: JSON.stringify({ username, password }),
  });
  if (!response.ok) throw await failure(response);
  return acceptToken(response, path);
};

export const logout = async (): Promise<void> => {
  signedOutOnPurpose = true;
  clearSession();
  try {
    const response = await authCall("/auth/logout", { method: HttpMethod.Post });
    if (!response.ok && response.status !== NO_CONTENT) await failure(response);
  } catch (error) {
    if (!(error instanceof ApiError)) throw error;
  }
};
