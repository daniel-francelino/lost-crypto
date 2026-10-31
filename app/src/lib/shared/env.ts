import { z } from "zod";

export const AppEnv = {
  Local: "local",
  Prod: "prod",
} as const;
export type AppEnv = (typeof AppEnv)[keyof typeof AppEnv];

const DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1";

export const envSchema = z.object({
  VITE_API_BASE_URL: z
    .string()
    .url()
    .default(DEFAULT_API_BASE_URL)
    .transform((value) => value.replace(/\/+$/, "")),
  VITE_APP_ENV: z.nativeEnum(AppEnv).default(AppEnv.Local),
});

export const parseEnv = (raw: Record<string, unknown>) => {
  const parsed = envSchema.parse(raw);
  return { apiBaseUrl: parsed.VITE_API_BASE_URL, appEnv: parsed.VITE_APP_ENV };
};

export const env = parseEnv(import.meta.env);
