import { z } from "zod";
import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { registeredSymbolSchema } from "@/lib/shared/market-data/registry.api";

export const PICKER_PAGE_SIZE = 30;

const availableSymbolSchema = z.object({
  symbol: z.string(),
  base: z.string(),
  quote_volume: z.string().nullable(),
  registry_id: z.string().nullable(),
  active: z.boolean(),
});
export type AvailableSymbol = z.infer<typeof availableSymbolSchema>;

const availablePageSchema = z.object({
  items: z.array(availableSymbolSchema),
  total: z.number(),
});
export type AvailablePage = z.infer<typeof availablePageSchema>;

export const listAvailableSymbols = (
  exchange: string,
  query: string,
  sort: string,
  offset: number,
  signal?: AbortSignal,
) =>
  request({
    path: "/trends/available",
    schema: availablePageSchema,
    query: { exchange, q: query.trim(), sort, limit: PICKER_PAGE_SIZE, offset },
    signal,
  });

export const addRegisteredSymbol = (exchange: string, symbol: string) =>
  request({
    method: HttpMethod.Post,
    path: "/trends/symbols",
    schema: registeredSymbolSchema,
    body: { exchange, symbol },
  });

export const setRegisteredSymbolActive = (id: string, active: boolean) =>
  request({
    method: HttpMethod.Post,
    path: `/trends/symbols/${id}/${active ? "activate" : "deactivate"}`,
    schema: registeredSymbolSchema,
  });
