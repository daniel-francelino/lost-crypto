import type { z } from "zod";
import { ApiError, HttpStatus } from "@/lib/shared/api/api-error";
import {
  HttpMethod,
  type Query,
  TOTAL_COUNT_HEADER,
  buildUrl,
  failure,
  readBody,
  send,
} from "@/lib/shared/api/http";
import { clearSession, getAccessToken, refreshSession } from "@/lib/shared/api/session";

const JSON_HEADERS = { "Content-Type": "application/json" };

export type RequestOptions<S extends z.ZodTypeAny> = {
  method?: HttpMethod;
  path: string;
  schema: S;
  query?: Query;
  body?: unknown;
  signal?: AbortSignal | undefined;
};

export type Paged<T> = { data: T; total: number };

const attempt = async (
  options: Omit<RequestOptions<z.ZodTypeAny>, "schema">,
): Promise<Response> => {
  const token = getAccessToken();
  return send(buildUrl(options.path, options.query), {
    method: options.method ?? HttpMethod.Get,
    headers: {
      ...(options.body === undefined ? {} : JSON_HEADERS),
      ...(token === null ? {} : { Authorization: `Bearer ${token}` }),
    },
    ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
    ...(options.signal ? { signal: options.signal } : {}),
  });
};

const execute = async (
  options: Omit<RequestOptions<z.ZodTypeAny>, "schema">,
): Promise<Response> => {
  const first = await attempt(options);
  if (first.status !== HttpStatus.Unauthorized) return first;
  const user = await refreshSession();
  if (user === null) {
    clearSession();
    return first;
  }
  return attempt(options);
};

const parse = <S extends z.ZodTypeAny>(schema: S, body: unknown, path: string): z.output<S> => {
  const parsed = schema.safeParse(body);
  if (!parsed.success) throw ApiError.invalidResponse(path);
  return parsed.data;
};

export const request = async <S extends z.ZodTypeAny>(
  options: RequestOptions<S>,
): Promise<z.output<S>> => {
  const response = await execute(options);
  if (!response.ok) throw await failure(response);
  return parse(options.schema, await readBody(response), options.path);
};

export const requestPaged = async <S extends z.ZodTypeAny>(
  options: RequestOptions<S>,
): Promise<Paged<z.output<S>>> => {
  const response = await execute(options);
  if (!response.ok) throw await failure(response);
  const data = parse(options.schema, await readBody(response), options.path);
  const total = Number.parseInt(response.headers.get(TOTAL_COUNT_HEADER) ?? "", 10);
  return { data, total: Number.isNaN(total) ? 0 : total };
};
