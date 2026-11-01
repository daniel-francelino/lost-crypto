import type { Backtest, BacktestInput } from "@/lib/backtests/backtests.api";
import { riskInput, riskValuesFrom } from "@/lib/backtests/form";
import { FillTiming, SlippageModel } from "@/lib/shared/enums";

export const COMPARISON_TIMEFRAMES = ["5m", "15m", "1h"] as const;

export const otherTimeframes = (current: string): string[] =>
  COMPARISON_TIMEFRAMES.filter((timeframe) => timeframe !== current);

const numericParams = (params: Record<string, unknown>): Record<string, number> =>
  Object.fromEntries(
    Object.entries(params).filter(
      (entry): entry is [string, number] => typeof entry[1] === "number",
    ),
  );

export type RunSource = Pick<
  Backtest,
  | "exchange"
  | "strategy_type"
  | "strategy_params"
  | "symbol"
  | "start"
  | "end"
  | "initial_capital"
  | "fee_rate"
  | "slippage_bps"
  | "slippage_model"
  | "slippage_k_range"
  | "slippage_k_size"
  | "seed"
  | "test_fraction"
  | "max_drawdown_tolerance_pct"
  | "max_drawdown_tolerance_days"
  | "allow_gaps"
  | "fill_timing"
  | "risk"
>;

export const inputWithTimeframe = (run: RunSource, timeframe: string): BacktestInput => ({
  exchange: run.exchange,
  strategy_type: run.strategy_type,
  strategy_params: numericParams(run.strategy_params),
  symbol: run.symbol,
  timeframe,
  start: run.start,
  end: run.end,
  initial_capital: run.initial_capital,
  fee_rate: run.fee_rate,
  slippage_bps: run.slippage_bps,
  slippage_model: run.slippage_model ?? SlippageModel.Fixed,
  slippage_k_range: run.slippage_k_range ?? "0",
  slippage_k_size: run.slippage_k_size ?? "0",
  seed: run.seed,
  test_fraction: run.test_fraction ?? null,
  cost_sensitivity: false,
  max_drawdown_tolerance_pct: run.max_drawdown_tolerance_pct ?? null,
  max_drawdown_tolerance_days: run.max_drawdown_tolerance_days ?? null,
  allow_gaps: run.allow_gaps ?? false,
  fill_timing: run.fill_timing ?? FillTiming.NextOpen,
  risk: run.risk === null || run.risk === undefined ? null : riskInput(riskValuesFrom(run.risk)),
});

export const hasStoredCandles = (present: number | undefined): boolean =>
  present !== undefined && present > 0;
