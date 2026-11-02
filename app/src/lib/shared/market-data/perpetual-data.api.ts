import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";

export type PerpetualAuxiliaryImportInput = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
};

export const requestPerpetualAuxiliaryImport = (body: PerpetualAuxiliaryImportInput) =>
  request({
    method: HttpMethod.Post,
    path: "/market-data/perpetual-data/import",
    schema: z.object({
      exchange: z.string(),
      symbol: z.string(),
      mark_candles_imported: z.number(),
      funding_events_imported: z.number(),
    }),
    body,
  });
