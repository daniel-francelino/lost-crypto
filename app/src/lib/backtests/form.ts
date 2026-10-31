import type { BacktestInput } from "@/lib/backtests/backtests.api";
import { dayEndUtcIso, dayStartUtcIso, daysAgoString } from "@/lib/shared/dates";
import { Timeframe } from "@/lib/shared/enums";
import {
  type ParamValues,
  buildStrategyParams,
  defaultParamValues,
  parseGridList,
} from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const MAX_COMBINATIONS = 200;
const DEFAULT_DAYS = 90;
const DEFAULT_TEST_FRACTION = "0.3";

export type BacktestFormValues = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  strategyType: string;
  params: ParamValues;
  initialCapital: string;
  feeRate: string;
  slippageBps: string;
  seed: string;
  testFraction: string;
  costSensitivity: boolean;
  toleranceDrawdownPct: string;
  toleranceDrawdownDays: string;
  sweep: boolean;
  grid: Record<string, string>;
};

export const defaultBacktestValues = (
  strategy: Strategy | undefined,
  now?: number,
): BacktestFormValues => ({
  exchange: "binance",
  symbol: "BTC/USDT",
  timeframe: Timeframe.H1,
  start: daysAgoString(DEFAULT_DAYS, now),
  end: daysAgoString(0, now),
  strategyType: strategy?.type_key ?? "",
  params: defaultParamValues(strategy),
  initialCapital: "1000",
  feeRate: "",
  slippageBps: "5",
  seed: "0",
  testFraction: DEFAULT_TEST_FRACTION,
  costSensitivity: false,
  toleranceDrawdownPct: "",
  toleranceDrawdownDays: "",
  sweep: false,
  grid: {},
});

export const buildGrid = (
  strategy: Strategy | undefined,
  grid: Record<string, string>,
): Record<string, number[]> | string => {
  const result: Record<string, number[]> = {};
  for (const param of strategy?.parameters ?? []) {
    const text = (grid[param.name] ?? "").trim();
    if (text === "") continue;
    const parsed = parseGridList(text, param.type === "integer");
    if (typeof parsed === "string") return `${param.name}: ${parsed}`;
    result[param.name] = parsed;
  }
  return result;
};

export const combinationCount = (grid: Record<string, number[]>): number =>
  Object.values(grid).reduce((total, values) => total * values.length, 1);

export const gridError = (grid: Record<string, number[]>): string | undefined => {
  if (Object.keys(grid).length === 0) return "Informe valores para ao menos um parâmetro.";
  const count = combinationCount(grid);
  return count > MAX_COMBINATIONS
    ? `São ${count} combinações; o máximo é ${MAX_COMBINATIONS}.`
    : undefined;
};

export const toBacktestInput = (
  values: BacktestFormValues,
  strategy: Strategy | undefined,
): BacktestInput => {
  const fraction = values.testFraction.trim();
  const fee = values.feeRate.trim();
  const tolerancePct = values.toleranceDrawdownPct.trim();
  const toleranceDays = values.toleranceDrawdownDays.trim();
  return {
    exchange: values.exchange,
    strategy_type: values.strategyType,
    strategy_params: buildStrategyParams(strategy, values.params),
    symbol: values.symbol.trim().toUpperCase(),
    timeframe: values.timeframe,
    start: dayStartUtcIso(values.start),
    end: dayEndUtcIso(values.end),
    initial_capital: values.initialCapital.trim(),
    fee_rate: fee === "" ? null : fee,
    slippage_bps: values.slippageBps.trim(),
    seed: Number.parseInt(values.seed.trim() === "" ? "0" : values.seed, 10),
    test_fraction: fraction === "" ? null : fraction,
    cost_sensitivity: values.costSensitivity && !values.sweep,
    max_drawdown_tolerance_pct: tolerancePct === "" ? null : tolerancePct,
    max_drawdown_tolerance_days: toleranceDays === "" ? null : Number.parseInt(toleranceDays, 10),
  };
};
