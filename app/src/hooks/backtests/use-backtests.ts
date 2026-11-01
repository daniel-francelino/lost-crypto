import { keepPreviousData, useQueries, useQuery } from "@tanstack/react-query";
import {
  compareBacktests,
  getBacktest,
  getBacktestEquity,
  getSweep,
  getTrades,
  getSizing,
  listBacktests,
} from "@/lib/backtests/backtests.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Poll, isJobFinished } from "@/lib/shared/polling";

export const useBacktests = (limit: number, offset: number) =>
  useQuery({
    queryKey: QueryKey.Backtests.list(limit, offset),
    queryFn: ({ signal }) => listBacktests(limit, offset, signal),
    placeholderData: keepPreviousData,
    refetchInterval: (query) =>
      (query.state.data?.data ?? []).some((run) => !isJobFinished(run.status)) ? Poll.Fast : false,
  });

export const useBacktest = (id: string) =>
  useQuery({
    queryKey: QueryKey.Backtests.detail(id),
    queryFn: ({ signal }) => getBacktest(id, signal),
    refetchInterval: (query) => (isJobFinished(query.state.data?.status) ? false : Poll.Fast),
  });

export const useTrades = (id: string, enabled: boolean) =>
  useQuery({
    queryKey: QueryKey.Backtests.trades(id),
    queryFn: ({ signal }) => getTrades(id, signal),
    enabled,
  });

export const useBacktestEquity = (id: string, enabled: boolean) =>
  useQuery({
    queryKey: QueryKey.Backtests.equity(id),
    queryFn: ({ signal }) => getBacktestEquity(id, signal),
    enabled,
  });

export const useSizing = (id: string, tolerable: string, scope: "day" | "bar", enabled: boolean) =>
  useQuery({
    queryKey: QueryKey.Backtests.sizing(id, tolerable, scope),
    queryFn: ({ signal }) => getSizing(id, tolerable, scope, signal),
    enabled,
  });

export const useSweep = (id: string) =>
  useQuery({
    queryKey: QueryKey.Backtests.sweep(id),
    queryFn: ({ signal }) => getSweep(id, signal),
    refetchInterval: (query) => {
      const data = query.state.data;
      const done = data !== undefined && data.completed + data.failed >= data.run_count;
      return done ? false : Poll.Fast;
    },
  });

export const useComparison = (ids: string[]) =>
  useQuery({
    queryKey: QueryKey.Backtests.compare(ids),
    queryFn: ({ signal }) => compareBacktests(ids, signal),
    enabled: ids.length > 0,
  });

export const useCompareEquity = (ids: string[]) =>
  useQueries({
    queries: ids.map((id) => ({
      queryKey: QueryKey.Backtests.equity(id),
      queryFn: ({ signal }: { signal: AbortSignal }) => getBacktestEquity(id, signal),
    })),
  });
