import { z } from "zod";
import { Role, Unknown } from "@/lib/shared/enums";

export const lenientEnum = <T extends Record<string, string>>(values: T) => {
  const known = new Set<string>(Object.values(values));
  return z.string().transform((value): T[keyof T] | Unknown => {
    return known.has(value) ? (value as T[keyof T]) : Unknown;
  });
};

export const decimalSchema = z.string();
export const nullableDecimalSchema = z.string().nullable();
export const timestampSchema = z.string();
export const nullableTimestampSchema = z.string().nullable();

export const userSchema = z.object({
  id: z.string(),
  username: z.string(),
  role: z.nativeEnum(Role),
  is_active: z.boolean(),
  created_at: z.string(),
  last_login_at: z.string().nullable(),
  can_write: z.boolean(),
});
export type User = z.infer<typeof userSchema>;

export const tokenSchema = z.object({
  access_token: z.string(),
  token_type: z.string(),
  expires_in: z.number(),
  user: userSchema,
});
export type TokenResponse = z.infer<typeof tokenSchema>;

export const emptySchema = z.unknown();
