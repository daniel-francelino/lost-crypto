import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  getBot,
  getBotEquity,
  getDivergence,
  getExecutionQuality,
  getInterventions,
  getOverview,
  getBacktestComparison,
  getParity,
  getPerformance,
  getPortfolio,
  getReadiness,
  getSummary,
  listBots,
  listOrders,
  listSignals,
  pauseBot,
  resetPortfolio,
  startBot,
  stopBot,
} from "@/lib/bots/bots.api";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { BotState } from "@/lib/shared/enums";
import { Poll, isJobFinished } from "@/lib/shared/polling";

export const EQUITY_LIMIT = 500;

export const useBots = () =>
  useQuery({ queryKey: QueryKey.Bots.list(), queryFn: ({ signal }) => listBots(signal) });

export const useOverview = () =>
  useQuery({
    queryKey: QueryKey.Bots.overview(),
    queryFn: ({ signal }) => getOverview(signal),
    refetchInterval: Poll.Overview,
  });

export const useInterventions = (id: string, days = 30) =>
  useQuery({
    queryKey: QueryKey.Bots.interventions(id, days),
    queryFn: ({ signal }) => getInterventions(id, days, signal),
    refetchInterval: Poll.Slow,
  });

export const useSummary = () =>
  useQuery({
    queryKey: QueryKey.Bots.summary(),
    queryFn: ({ signal }) => getSummary(signal),
    refetchInterval: Poll.Overview,
  });

export const useBot = (id: string, enabled = true) =>
  useQuery({
    queryKey: QueryKey.Bots.detail(id),
    enabled,
    queryFn: ({ signal }) => getBot(id, signal),
    refetchInterval: (query) => {
      const bot = query.state.data;
      const converging = bot !== undefined && bot.desired_state !== bot.observed_state;
      return converging ? Poll.Fast : Poll.Detail;
    },
  });

export const usePortfolio = (id: string) =>
  useQuery({
    queryKey: QueryKey.Bots.portfolio(id),
    queryFn: ({ signal }) => getPortfolio(id, signal),
    refetchInterval: Poll.Detail,
  });

export const usePerformance = (id: string, enabled = true) =>
  useQuery({
    queryKey: QueryKey.Bots.performance(id),
    enabled,
    queryFn: ({ signal }) => getPerformance(id, signal),
    refetchInterval: Poll.Slow,
  });

export const useBotEquity = (id: string) =>
  useQuery({
    queryKey: QueryKey.Bots.equity(id, EQUITY_LIMIT),
    queryFn: ({ signal }) => getBotEquity(id, EQUITY_LIMIT, signal),
    refetchInterval: Poll.Slow,
  });

export const useOrders = (id: string, limit: number, offset: number, enabled = true) =>
  useQuery({
    queryKey: QueryKey.Bots.orders(id, limit, offset),
    enabled,
    queryFn: ({ signal }) => listOrders(id, limit, offset, signal),
    placeholderData: keepPreviousData,
    refetchInterval: Poll.Detail,
  });

export const useSignals = (id: string, limit: number, offset: number) =>
  useQuery({
    queryKey: QueryKey.Bots.signals(id, limit, offset),
    queryFn: ({ signal }) => listSignals(id, limit, offset, signal),
    placeholderData: keepPreviousData,
    refetchInterval: Poll.Detail,
  });

export const useReadiness = (id: string, enabled: boolean) =>
  useQuery({
    queryKey: QueryKey.Bots.readiness(id),
    queryFn: ({ signal }) => getReadiness(id, signal),
    enabled,
  });

export const BotCommand = {
  Start: "start",
  Pause: "pause",
  Stop: "stop",
  Reset: "reset",
} as const;
export type BotCommand = (typeof BotCommand)[keyof typeof BotCommand];

export const useBotCommand = (id: string) => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({
      command,
      token,
      reason,
    }: {
      command: BotCommand;
      token?: string | null;
      reason?: string;
    }) => {
      if (command === BotCommand.Start) return startBot(id, token ?? null);
      if (command === BotCommand.Pause) return pauseBot(id, reason);
      if (command === BotCommand.Stop) return stopBot(id, reason);
      return resetPortfolio(id, reason);
    },
    onSettled: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.Bots.all() });
    },
  });
};

export const isConverging = (desired: string, observed: string): boolean =>
  desired !== observed && !(desired === BotState.Stopped && observed === BotState.Error);

export const useExecutionQuality = (id: string) =>
  useQuery({
    queryKey: QueryKey.Bots.executionQuality(id),
    queryFn: ({ signal }) => getExecutionQuality(id, signal),
    refetchInterval: Poll.Detail,
  });

export const useParity = (id: string) =>
  useQuery({
    queryKey: QueryKey.Bots.parity(id),
    queryFn: ({ signal }) => getParity(id, signal),
    refetchInterval: (query) =>
      query.state.data !== null &&
      query.state.data !== undefined &&
      !isJobFinished(query.state.data.status)
        ? Poll.Fast
        : false,
  });

export const useBacktestComparison = (id: string, runId = "") =>
  useQuery({
    queryKey: QueryKey.Bots.backtestComparison(id, runId),
    queryFn: ({ signal }) => getBacktestComparison(id, runId === "" ? undefined : runId, signal),
    refetchInterval: Poll.Detail,
  });

export const useDivergence = (id: string) =>
  useQuery({
    queryKey: QueryKey.Bots.divergence(id),
    queryFn: ({ signal }) => getDivergence(id, signal),
  });
