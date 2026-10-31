import { z } from "zod";
import { requestPaged } from "@/lib/shared/api/client";

const auditEventSchema = z.object({
  occurred_at: z.string().nullable(),
  actor: z.string(),
  event_type: z.string(),
  entity_type: z.string(),
  entity_id: z.string(),
  bot_id: z.string().nullable(),
  payload: z.record(z.string(), z.unknown()),
});
export type AuditEvent = z.infer<typeof auditEventSchema>;

export type AuditFilters = {
  botId: string | null;
  eventType: string | null;
  limit: number;
  offset: number;
};

export const listAudit = (filters: AuditFilters, signal?: AbortSignal) =>
  requestPaged({
    path: "/audit-events",
    schema: z.array(auditEventSchema),
    query: {
      bot_id: filters.botId,
      event_type: filters.eventType,
      limit: filters.limit,
      offset: filters.offset,
    },
    signal,
  });
