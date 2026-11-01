import { z } from "zod";
import { request, requestPaged } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";

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

export const NOTE_EVENT = "note.added";
const NOTES_LIMIT = 50;

export const NoteTarget = { Bot: "bots", Backtest: "backtests" } as const;
export type NoteTarget = (typeof NoteTarget)[keyof typeof NoteTarget];

export const listNotes = (entityId: string, signal?: AbortSignal) =>
  requestPaged({
    path: "/audit-events",
    schema: z.array(auditEventSchema),
    query: { event_type: NOTE_EVENT, entity_id: entityId, limit: NOTES_LIMIT },
    signal,
  });

const noteSchema = z.object({ actor: z.string(), text: z.string() });

export const addNote = (target: NoteTarget, id: string, text: string) =>
  request({
    method: HttpMethod.Post,
    path: `/${target}/${id}/notes`,
    body: { text },
    schema: noteSchema,
  });
