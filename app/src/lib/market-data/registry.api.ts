import { request } from "@/lib/shared/api/client";
import { HttpMethod } from "@/lib/shared/api/http";
import { registeredSymbolSchema } from "@/lib/shared/market-data/registry.api";

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
