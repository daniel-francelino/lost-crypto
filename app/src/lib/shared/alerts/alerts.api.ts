import { z } from "zod";
import { request, requestPaged } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import {
  emptySchema,
  lenientEnum,
  nullableTimestampSchema,
  timestampSchema,
} from "@/lib/shared/api/schemas";
import { AlertKind, AlertSeverity } from "@/lib/shared/enums";

const alertSchema = z.object({
  id: z.number(),
  kind: lenientEnum(AlertKind),
  severity: lenientEnum(AlertSeverity),
  message: z.string(),
  bot_id: z.string().nullable(),
  payload: z.record(z.string(), z.unknown()),
  opened_at: timestampSchema,
  resolved_at: nullableTimestampSchema,
  read_at: nullableTimestampSchema,
});
export type Alert = z.infer<typeof alertSchema>;

const summarySchema = z.object({
  unread: z.number(),
  open: z.number(),
  critical_open: z.number(),
});
export type AlertSummary = z.infer<typeof summarySchema>;

const markedSchema = z.object({ marked: z.number() });

export type AlertFilters = {
  unreadOnly: boolean;
  severity: AlertSeverity | null;
  limit: number;
  offset: number;
};

export const listAlerts = (filters: AlertFilters, signal?: AbortSignal) =>
  requestPaged({
    path: "/alerts",
    schema: z.array(alertSchema),
    query: {
      unread: filters.unreadOnly,
      severity: filters.severity,
      limit: filters.limit,
      offset: filters.offset,
    },
    signal,
  });

export const getAlertSummary = (signal?: AbortSignal): Promise<AlertSummary> =>
  request({ path: "/alerts/summary", schema: summarySchema, signal });

export const markAlertRead = (id: number): Promise<unknown> =>
  request({ method: HttpMethod.Post, path: `/alerts/${id}/read`, schema: emptySchema });

export const markAllAlertsRead = (): Promise<number> =>
  request({ method: HttpMethod.Post, path: "/alerts/read-all", schema: markedSchema }).then(
    (result) => result.marked,
  );
