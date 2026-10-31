import { env } from "@/lib/shared/env";
import { ApiError } from "@/lib/shared/api/api-error";

export const HttpMethod = {
  Get: "GET",
  Post: "POST",
  Put: "PUT",
  Patch: "PATCH",
  Delete: "DELETE",
} as const;
export type HttpMethod = (typeof HttpMethod)[keyof typeof HttpMethod];

export const NO_CONTENT = 204;
export const TOTAL_COUNT_HEADER = "X-Total-Count";

export type Query = Record<string, string | number | boolean | null | undefined | string[]>;

export const buildUrl = (path: string, query?: Query): string => {
  const url = new URL(`${env.apiBaseUrl}${path}`);
  for (const [key, value] of Object.entries(query ?? {})) {
    if (value === null || value === undefined || value === "") continue;
    if (Array.isArray(value)) {
      for (const item of value) url.searchParams.append(key, item);
      continue;
    }
    url.searchParams.set(key, String(value));
  }
  return url.toString();
};

export const readBody = async (response: Response): Promise<unknown> => {
  if (response.status === NO_CONTENT) return null;
  const text = await response.text();
  if (text === "") return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
};

export const send = async (url: string, init: RequestInit): Promise<Response> => {
  try {
    return await fetch(url, init);
  } catch (error) {
    if (error instanceof DOMException && error.name === "AbortError") throw error;
    throw ApiError.network();
  }
};

export const failure = async (response: Response): Promise<ApiError> =>
  ApiError.fromBody(response.status, await readBody(response));
