import { useQuery } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { listSupportedPairs } from "@/lib/shared/market-data/pairs.api";

const PAIRS_STALE_MS = 60 * 60_000;

export const useSupportedPairs = () =>
  useQuery({
    queryKey: QueryKey.MarketData.symbols(),
    queryFn: ({ signal }) => listSupportedPairs(signal),
    staleTime: PAIRS_STALE_MS,
  });
