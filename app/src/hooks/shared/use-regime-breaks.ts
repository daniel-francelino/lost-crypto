import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import {
  type RegimeBreakInput,
  type RegimeBreakScope,
  createRegimeBreak,
  deleteRegimeBreak,
  listRegimeBreaks,
} from "@/lib/shared/market-data/regime-breaks.api";

export const useRegimeBreaks = (scope: RegimeBreakScope = {}, enabled = true) =>
  useQuery({
    queryKey: QueryKey.MarketData.regimeBreaks(scope.exchange ?? "", scope.symbol ?? ""),
    queryFn: ({ signal }) => listRegimeBreaks(scope, signal),
    enabled,
  });

export const useCreateRegimeBreak = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (body: RegimeBreakInput) => createRegimeBreak(body),
    onSuccess: () => client.invalidateQueries({ queryKey: QueryKey.MarketData.regimeBreaksAll() }),
  });
};

export const useDeleteRegimeBreak = () => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteRegimeBreak(id),
    onSuccess: () => client.invalidateQueries({ queryKey: QueryKey.MarketData.regimeBreaksAll() }),
  });
};
