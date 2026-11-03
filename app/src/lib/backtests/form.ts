import type { BacktestInput, RiskInput } from "@/lib/backtests/backtests.api";
import { type BacktestPrefill, parseJsonRecord } from "@/lib/shared/backtest-prefill";
import { dayEndUtcIso, dayStartUtcIso, daysAgoString } from "@/lib/shared/dates";
import {
  DrawdownAction,
  FillTiming,
  MarginMode,
  SlippageModel,
  Timeframe,
  TradingProduct,
} from "@/lib/shared/enums";
import { compareDecimal, trimDecimalZeros } from "@/lib/shared/format";
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

export const CAPITAL_ITEMS = [
  { label: "100 USDT", value: "100" },
  { label: "1.000 USDT", value: "1000" },
];
export const DEFAULT_CAPITAL = "1000";

export type BacktestFormValues = {
  exchange: string;
  connectionId: string;
  product: string;
  leverage: string;
  allowShort: boolean;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  strategyType: string;
  params: ParamValues;
  initialCapital: string;
  feeRate: string;
  slippageBps: string;
  slippageModel: string;
  slippageKRange: string;
  slippageKSize: string;
  seed: string;
  testFraction: string;
  costSensitivity: boolean;
  toleranceDrawdownPct: string;
  toleranceDrawdownDays: string;
  allowGaps: boolean;
  sweep: boolean;
  grid: Record<string, string>;
  fillTiming: string;
  riskEnabled: boolean;
  risk: RiskValues;
};

export type RiskValues = {
  maxPositionFraction: string;
  maxOrderNotional: string;
  maxDailyLossPct: string;
  maxDrawdownPct: string;
  maxConsecutiveLosses: string;
  maxRiskPerTradePct: string;
  minLiquidationDistancePct: string;
  requireStopLoss: boolean;
  maxCandleRangePct: string;
  maxOrderPctOfVolume: string;
  maxCloseJumpPct: string;
  drawdownAction: string;
};

export const DEFAULT_RISK: RiskValues = {
  maxPositionFraction: "1",
  maxOrderNotional: "",
  maxDailyLossPct: "10",
  maxDrawdownPct: "",
  maxConsecutiveLosses: "",
  maxRiskPerTradePct: "",
  minLiquidationDistancePct: "",
  requireStopLoss: false,
  maxCandleRangePct: "25",
  maxOrderPctOfVolume: "",
  maxCloseJumpPct: "",
  drawdownAction: DrawdownAction.Pause,
};

export const defaultBacktestValues = (
  strategy: Strategy | undefined,
  now?: number,
): BacktestFormValues => ({
  exchange: "binance",
  connectionId: "",
  product: TradingProduct.Spot,
  leverage: "1",
  allowShort: false,
  symbol: "BTC/USDT",
  timeframe: Timeframe.H1,
  start: daysAgoString(DEFAULT_DAYS, now),
  end: daysAgoString(0, now),
  strategyType: strategy?.type_key ?? "",
  params: defaultParamValues(strategy),
  initialCapital: DEFAULT_CAPITAL,
  feeRate: "",
  slippageBps: "5",
  slippageModel: SlippageModel.Fixed,
  slippageKRange: "",
  slippageKSize: "",
  seed: "0",
  testFraction: DEFAULT_TEST_FRACTION,
  costSensitivity: false,
  toleranceDrawdownPct: "",
  toleranceDrawdownDays: "",
  allowGaps: false,
  sweep: false,
  grid: {},
  fillTiming: FillTiming.NextOpen,
  riskEnabled: false,
  risk: DEFAULT_RISK,
});

import { START_OFFSET_KEY } from "@/lib/backtests/start-sensitivity";

const offsetsAxis = (grid: Record<string, string>): number[] | string | null => {
  const text = (grid[START_OFFSET_KEY] ?? "").trim();
  if (text === "") return null;
  const parsed = parseGridList(text, true);
  return typeof parsed === "string" ? `Dias de deslocamento: ${parsed}` : parsed;
};

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
  const offsets = offsetsAxis(grid);
  if (typeof offsets === "string") return offsets;
  if (offsets !== null) result[START_OFFSET_KEY] = offsets;
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
    connection_id: values.connectionId || null,
    product: values.product,
    leverage: Number.parseInt(values.leverage || "1", 10),
    margin_mode: values.product === TradingProduct.LinearPerpetual ? MarginMode.Isolated : null,
    allow_short: values.product === TradingProduct.LinearPerpetual && values.allowShort,
    strategy_type: values.strategyType,
    strategy_params: buildStrategyParams(strategy, values.params),
    symbol: values.symbol.trim().toUpperCase(),
    timeframe: values.timeframe,
    start: dayStartUtcIso(values.start),
    end: dayEndUtcIso(values.end),
    initial_capital: values.initialCapital.trim(),
    fee_rate: fee === "" ? null : fee,
    slippage_bps: values.slippageBps.trim(),
    slippage_model: values.slippageModel,
    slippage_k_range: values.slippageKRange.trim() === "" ? "0" : values.slippageKRange.trim(),
    slippage_k_size: values.slippageKSize.trim() === "" ? "0" : values.slippageKSize.trim(),
    seed: Number.parseInt(values.seed.trim() === "" ? "0" : values.seed, 10),
    test_fraction: fraction === "" ? null : fraction,
    cost_sensitivity: values.costSensitivity && !values.sweep,
    max_drawdown_tolerance_pct: tolerancePct === "" ? null : tolerancePct,
    max_drawdown_tolerance_days: toleranceDays === "" ? null : Number.parseInt(toleranceDays, 10),
    allow_gaps: values.allowGaps,
    fill_timing: values.fillTiming,
    risk: values.riskEnabled ? riskInput(values.risk) : null,
  };
};

export const MIN_TEST_FRACTION = "0.25";
export const BARS_PER_PARAMETER = 252;
export const MAX_PARAMETERS = 5;

export const testFractionWarning = (fraction: string): string | undefined => {
  const text = fraction.trim();
  if (text === "" || compareDecimal(text, "0") <= 0) return undefined;
  if (compareDecimal(text, MIN_TEST_FRACTION) >= 0) return undefined;
  return "O livro sugere o teste com pelo menos ⅓ do treino (fração ≥ 0.25): com menos, o resultado fora da amostra pesa pouco.";
};

export const freeParameterCount = (strategy: Strategy | undefined, values: ParamValues): number =>
  (strategy?.parameters ?? []).filter((param) => (values[param.name] ?? "").trim() !== "").length;

export type SampleAdvice = { freeParameters: number; minBars: number; enough: boolean };

export const sampleAdvice = (
  strategy: Strategy | undefined,
  values: ParamValues,
  expectedBars: number,
): SampleAdvice => {
  const freeParameters = freeParameterCount(strategy, values);
  const minBars = BARS_PER_PARAMETER * freeParameters;
  return { freeParameters, minBars, enough: expectedBars >= minBars };
};

const blankToNull = (text: string): string | null => (text.trim() === "" ? null : text.trim());

export const riskInput = (risk: RiskValues): RiskInput => ({
  max_position_fraction: risk.maxPositionFraction.trim() || "1",
  max_order_notional: blankToNull(risk.maxOrderNotional),
  max_daily_loss_pct: blankToNull(risk.maxDailyLossPct),
  max_drawdown_pct: blankToNull(risk.maxDrawdownPct),
  max_consecutive_losses:
    risk.maxConsecutiveLosses.trim() === "" ? null : Number.parseInt(risk.maxConsecutiveLosses, 10),
  max_risk_per_trade_pct: blankToNull(risk.maxRiskPerTradePct),
  min_liquidation_distance_pct: blankToNull(risk.minLiquidationDistancePct),
  require_stop_loss: risk.requireStopLoss,
  max_candle_range_pct: blankToNull(risk.maxCandleRangePct),
  max_order_pct_of_volume: blankToNull(risk.maxOrderPctOfVolume),
  max_close_jump_pct: blankToNull(risk.maxCloseJumpPct),
  drawdown_action: risk.drawdownAction,
});

const textOf = (value: unknown): string =>
  value === null || value === undefined ? "" : trimDecimalZeros(String(value));

export const riskValuesFrom = (raw: Record<string, unknown>): RiskValues => ({
  maxPositionFraction: textOf(raw["max_position_fraction"]) || "1",
  maxOrderNotional: textOf(raw["max_order_notional"]),
  maxDailyLossPct: textOf(raw["max_daily_loss_pct"]),
  maxDrawdownPct: textOf(raw["max_drawdown_pct"]),
  maxConsecutiveLosses: textOf(raw["max_consecutive_losses"]),
  maxRiskPerTradePct: textOf(raw["max_risk_per_trade_pct"]),
  minLiquidationDistancePct: textOf(raw["min_liquidation_distance_pct"]),
  requireStopLoss: raw["require_stop_loss"] === true,
  maxCandleRangePct: textOf(raw["max_candle_range_pct"]),
  maxOrderPctOfVolume: textOf(raw["max_order_pct_of_volume"]),
  maxCloseJumpPct: textOf(raw["max_close_jump_pct"]),
  drawdownAction: textOf(raw["drawdown_action"]) || DrawdownAction.Pause,
});

export const applyBacktestPrefill = (
  values: BacktestFormValues,
  prefill: BacktestPrefill,
  strategies: Strategy[],
): BacktestFormValues => {
  const product = prefill.product ?? values.product;
  const strategy = strategies.find((item) => item.type_key === prefill.strategy);
  const risk = parseJsonRecord(prefill.risk);
  const params = parseJsonRecord(prefill.params);
  return {
    ...values,
    product,
    exchange:
      prefill.product === undefined
        ? values.exchange
        : product === TradingProduct.LinearPerpetual
          ? "binance-usdm"
          : "binance",
    connectionId: prefill.connectionId ?? values.connectionId,
    leverage: prefill.leverage ?? values.leverage,
    allowShort: prefill.allowShort ?? values.allowShort,
    symbol: prefill.symbol ?? values.symbol,
    timeframe: prefill.timeframe ?? values.timeframe,
    strategyType: strategy?.type_key ?? values.strategyType,
    params:
      strategy === undefined
        ? values.params
        : {
            ...defaultParamValues(strategy),
            ...Object.fromEntries(Object.entries(params).map(([k, v]) => [k, textOf(v)])),
          },
    feeRate: prefill.feeRate === undefined ? values.feeRate : trimDecimalZeros(prefill.feeRate),
    initialCapital:
      prefill.initialCapital === undefined
        ? values.initialCapital
        : trimDecimalZeros(prefill.initialCapital),
    slippageBps:
      prefill.slippageBps === undefined
        ? values.slippageBps
        : trimDecimalZeros(prefill.slippageBps),
    fillTiming: prefill.fillTiming ?? values.fillTiming,
    riskEnabled: prefill.risk !== undefined,
    risk: prefill.risk === undefined ? values.risk : riskValuesFrom(risk),
  };
};
