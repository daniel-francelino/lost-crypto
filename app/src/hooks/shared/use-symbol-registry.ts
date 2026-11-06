import { useQuery } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { listRegisteredSymbols, listTrends } from "@/lib/shared/market-data/registry.api";
import { Poll } from "@/lib/shared/polling";

const REGISTRY_STALE_MS = 30_000;

export const useRegisteredSymbols = () =>
  useQuery({
    queryKey: QueryKey.Trends.symbols(),
    queryFn: ({ signal }) => listRegisteredSymbols(signal),
    staleTime: REGISTRY_STALE_MS,
  });

export const useTrends = () =>
  useQuery({
    queryKey: QueryKey.Trends.latest(),
    queryFn: ({ signal }) => listTrends(signal),
    refetchInterval: Poll.Trends,
  });
