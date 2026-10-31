import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { lenientEnum, nullableTimestampSchema } from "@/lib/shared/api/schemas";
import { ConnectionStatus, Environment } from "@/lib/shared/enums";

const permissionsSchema = z.object({
  can_read: z.boolean(),
  can_trade: z.boolean(),
  can_withdraw: z.boolean(),
  can_transfer: z.boolean(),
  ip_restricted: z.boolean(),
});
export type Permissions = z.infer<typeof permissionsSchema>;

export const connectionSchema = z.object({
  id: z.string(),
  exchange: z.string(),
  environment: lenientEnum(Environment),
  label: z.string(),
  api_key_hint: z.string(),
  status: lenientEnum(ConnectionStatus),
  created_at: z.string(),
  verified_at: nullableTimestampSchema,
  permissions: permissionsSchema.nullish(),
  status_reason: z.string().nullish(),
  last_checked_at: z.string().nullish(),
  permission_warning: z.string().nullish(),
});
export type Connection = z.infer<typeof connectionSchema>;

export const listConnections = (signal?: AbortSignal): Promise<Connection[]> =>
  request({ path: "/exchange-connections", schema: z.array(connectionSchema), signal });

export type PermissionItem = { key: string; ok: boolean; text: string };

export const permissionItems = (permissions: Permissions): PermissionItem[] => [
  {
    key: "trade",
    ok: permissions.can_trade,
    text: permissions.can_trade ? "Negocia" : "Não negocia",
  },
  {
    key: "withdraw",
    ok: !permissions.can_withdraw,
    text: permissions.can_withdraw ? "PODE SACAR" : "Sem saque",
  },
  {
    key: "transfer",
    ok: !permissions.can_transfer,
    text: permissions.can_transfer ? "Pode transferir" : "Sem transferência",
  },
  {
    key: "ip",
    ok: permissions.ip_restricted,
    text: permissions.ip_restricted ? "IP restrito" : "Qualquer IP",
  },
];
