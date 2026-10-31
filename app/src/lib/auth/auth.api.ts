import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { emptySchema, userSchema } from "@/lib/shared/api/schemas";
import type { Role } from "@/lib/shared/enums";

export const listUsers = (signal?: AbortSignal) =>
  request({ path: "/auth/users", schema: z.array(userSchema), signal });

export const createUser = (username: string, password: string, role: Role) =>
  request({
    method: HttpMethod.Post,
    path: "/auth/users",
    schema: userSchema,
    body: { username, password, role },
  });

export const setUserActive = (id: string, active: boolean) =>
  request({
    method: HttpMethod.Post,
    path: `/auth/users/${id}/${active ? "enable" : "disable"}`,
    schema: emptySchema,
  });

export const changePassword = (currentPassword: string, newPassword: string) =>
  request({
    method: HttpMethod.Post,
    path: "/auth/change-password",
    schema: emptySchema,
    body: { current_password: currentPassword, new_password: newPassword },
  });
