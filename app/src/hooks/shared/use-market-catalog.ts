import { useQuery } from "@tanstack/react-query";
import { listMarkets } from "@/lib/shared/market-data/markets.api";
import { QueryKey } from "@/lib/shared/api/query-keys";

export const useMarketCatalog = (exchange: string, enabled = true) =>
  useQuery({
    queryKey: QueryKey.MarketData.catalog(exchange),
    queryFn: ({ signal }) => listMarkets(exchange, signal),
    enabled,
    staleTime: 60 * 60_000,
  });
