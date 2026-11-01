import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";

const regimeBreakSchema = z.object({
  id: z.string(),
  name: z.string(),
  occurred_at: z.string(),
  exchange: z.string().nullable(),
  symbol: z.string().nullable(),
  note: z.string().nullable(),
  created_by: z.string(),
  created_at: z.string(),
});
export type RegimeBreak = z.infer<typeof regimeBreakSchema>;

export type RegimeBreakScope = { exchange?: string; symbol?: string };

export const listRegimeBreaks = (scope: RegimeBreakScope, signal?: AbortSignal) =>
  request({
    path: "/market-data/regime-breaks",
    schema: z.array(regimeBreakSchema),
    query: { exchange: scope.exchange ?? null, symbol: scope.symbol ?? null },
    signal,
  });

export type RegimeBreakInput = {
  name: string;
  occurred_at: string;
  exchange: string | null;
  symbol: string | null;
  note: string | null;
};

export const createRegimeBreak = (body: RegimeBreakInput) =>
  request({
    method: HttpMethod.Post,
    path: "/market-data/regime-breaks",
    body,
    schema: regimeBreakSchema,
  });

export const deleteRegimeBreak = (id: string) =>
  request({
    method: HttpMethod.Delete,
    path: `/market-data/regime-breaks/${id}`,
    schema: z.unknown(),
  });
