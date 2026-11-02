import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import {
  decimalSchema,
  nullableDecimalSchema,
  nullableTimestampSchema,
} from "@/lib/shared/api/schemas";

const killSwitchSchema = z.object({
  active: z.boolean(),
  reason: z.string().nullable(),
  changed_at: nullableTimestampSchema,
  close_futures_positions: z.boolean().optional().default(false),
});
export type KillSwitch = z.infer<typeof killSwitchSchema>;

const backupRecordSchema = z.object({
  at: z.string(),
  ok: z.boolean(),
  file: z.string().nullable(),
  size_bytes: z.number().nullable(),
  detail: z.string().nullable(),
});
export type BackupRecord = z.infer<typeof backupRecordSchema>;

const statusSchema = z.object({
  worker: z.object({
    alive: z.boolean(),
    last_heartbeat_at: nullableTimestampSchema,
    age_seconds: z.number().nullable(),
  }),
  kill_switch: killSwitchSchema,
  bots_by_state: z.record(z.string(), z.number()),
  stale_bots: z.array(
    z.object({
      bot_id: z.string(),
      name: z.string(),
      last_heartbeat_at: nullableTimestampSchema,
      age_seconds: z.number().nullable(),
    }),
  ),
  exchanges: z.array(z.string()),
  unprotected_positions: z
    .array(
      z.object({
        bot_id: z.string(),
        name: z.string(),
        symbol: z.string(),
        mode: z.string(),
        quantity: decimalSchema,
        stop_price: nullableDecimalSchema,
      }),
    )
    .optional(),
  clock: z
    .object({
      skew_ms: z.number().nullable(),
      measured_at: nullableTimestampSchema,
      warning: z.boolean(),
      blocking_live: z.boolean(),
    })
    .nullish(),
  backup: z
    .object({
      last_backup: backupRecordSchema.nullable(),
      last_restore_check: backupRecordSchema.nullable(),
      overdue: z.boolean(),
    })
    .nullish(),
});
export type SystemStatus = z.infer<typeof statusSchema>;

const capabilitiesSchema = z.object({
  environment: z.string(),
  testnet_trading_enabled: z.boolean(),
  live_trading_enabled: z.boolean(),
  live_available: z.boolean(),
  live_blockers: z.array(z.string()),
  live_min_paper_days: z.number(),
  live_approval_minutes: z.number(),
  exchanges: z.array(z.string()),
  strategies: z.array(z.string()),
});
export type Capabilities = z.infer<typeof capabilitiesSchema>;

export const getStatus = (signal?: AbortSignal): Promise<SystemStatus> =>
  request({ path: "/system/status", schema: statusSchema, signal });

export const getCapabilities = (signal?: AbortSignal): Promise<Capabilities> =>
  request({ path: "/system/capabilities", schema: capabilitiesSchema, signal });

export const setKillSwitch = (
  active: boolean,
  reason: string | null,
  closeFuturesPositions = false,
): Promise<KillSwitch> =>
  request({
    method: HttpMethod.Put,
    path: "/system/kill-switch",
    schema: killSwitchSchema,
    body: { active, reason, close_futures_positions: closeFuturesPositions },
  });

export const WORKER_HEALTH_PATH = "/health/worker";
