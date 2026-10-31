import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { lenientEnum, nullableTimestampSchema } from "@/lib/shared/api/schemas";
import { ConnectionStatus, Environment } from "@/lib/shared/enums";

export const connectionSchema = z.object({
  id: z.string(),
  exchange: z.string(),
  environment: lenientEnum(Environment),
  label: z.string(),
  api_key_hint: z.string(),
  status: lenientEnum(ConnectionStatus),
  created_at: z.string(),
  verified_at: nullableTimestampSchema,
});
export type Connection = z.infer<typeof connectionSchema>;

export const listConnections = (signal?: AbortSignal): Promise<Connection[]> =>
  request({ path: "/exchange-connections", schema: z.array(connectionSchema), signal });
