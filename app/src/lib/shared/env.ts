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

const LOCAL_HOSTS = new Set(["localhost", "127.0.0.1", "[::1]"]);

export const environmentWarning = (apiBaseUrl: string, appEnv: AppEnv): string | null => {
  const local = LOCAL_HOSTS.has(new URL(apiBaseUrl).hostname);
  if (appEnv === AppEnv.Prod && local) {
    return "Esta é uma versão de produção apontando para um servidor local.";
  }
  if (appEnv === AppEnv.Local && !local) {
    return "Esta versão está marcada como local, mas aponta para um servidor remoto.";
  }
  return null;
};
