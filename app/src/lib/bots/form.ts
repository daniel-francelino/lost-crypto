import type { Bot, BotInput } from "@/lib/bots/bots.api";
import { estimateLeveragedEntry } from "@/lib/shared/format";
import {
  DrawdownAction,
  ExecutionMode,
  MarginMode,
  Timeframe,
  TradingProduct,
} from "@/lib/shared/enums";
import {
  type ParamValues,
  buildStrategyParams,
  defaultParamValues,
  paramsFromRecord,
} from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const DEFAULT_EXCHANGE = "binance";
const DEFAULT_SYMBOL = "BTC/USDT";

export type BotFormValues = {
  name: string;
  exchange: string;
  product: TradingProduct;
  leverage: string;
  allowShort: boolean;
  symbol: string;
  timeframe: string;
  strategyType: string;
  params: ParamValues;
  initialCapital: string;
  feeRate: string;
  slippageBps: string;
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
  mode: string;
  connectionId: string;
};

export const defaultFormValues = (strategy: Strategy | undefined): BotFormValues => ({
  name: "",
  exchange: DEFAULT_EXCHANGE,
  product: TradingProduct.Spot,
  leverage: "1",
  allowShort: false,
  symbol: DEFAULT_SYMBOL,
  timeframe: Timeframe.H1,
  strategyType: strategy?.type_key ?? "",
  params: defaultParamValues(strategy),
  initialCapital: "1000",
  feeRate: "",
  slippageBps: "5",
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
  mode: ExecutionMode.Paper,
  connectionId: "",
});

const text = (value: string | number | null): string => (value === null ? "" : String(value));

export const formFromBot = (bot: Bot, strategy: Strategy | undefined): BotFormValues => ({
  name: bot.name,
  exchange: bot.exchange,
  product:
    bot.product === TradingProduct.LinearPerpetual
      ? TradingProduct.LinearPerpetual
      : TradingProduct.Spot,
  leverage: String(bot.leverage ?? 1),
  allowShort: bot.allow_short ?? false,
  symbol: bot.symbol,
  timeframe: bot.timeframe,
  strategyType: bot.strategy_type,
  params: paramsFromRecord(strategy, bot.strategy_params),
  initialCapital: bot.initial_capital,
  feeRate: bot.fee_rate,
  slippageBps: bot.slippage_bps,
  maxPositionFraction: bot.risk.max_position_fraction,
  maxOrderNotional: text(bot.risk.max_order_notional),
  maxDailyLossPct: text(bot.risk.max_daily_loss_pct),
  maxDrawdownPct: text(bot.risk.max_drawdown_pct),
  maxConsecutiveLosses: text(bot.risk.max_consecutive_losses),
  maxRiskPerTradePct: text(bot.risk.max_risk_per_trade_pct),
  minLiquidationDistancePct: text(bot.risk.min_liquidation_distance_pct ?? null),
  requireStopLoss: bot.risk.require_stop_loss,
  maxCandleRangePct: text(bot.risk.max_candle_range_pct),
  maxOrderPctOfVolume: text(bot.risk.max_order_pct_of_volume ?? null),
  maxCloseJumpPct: text(bot.risk.max_close_jump_pct ?? null),
  drawdownAction: bot.risk.drawdown_action ?? DrawdownAction.Pause,
  mode: bot.mode,
  connectionId: bot.connection_id ?? "",
});

const nullable = (value: string): string | null => (value.trim() === "" ? null : value.trim());

export const toBotInput = (values: BotFormValues, strategy: Strategy | undefined): BotInput => ({
  name: values.name.trim(),
  exchange: values.exchange,
  product: values.product,
  leverage: Number.parseInt(values.leverage, 10),
  margin_mode: values.product === TradingProduct.LinearPerpetual ? MarginMode.Isolated : null,
  allow_short: values.product === TradingProduct.LinearPerpetual && values.allowShort,
  strategy_type: values.strategyType,
  strategy_params: buildStrategyParams(strategy, values.params),
  symbol: values.symbol.trim().toUpperCase(),
  timeframe: Object.values(Timeframe).find((item) => item === values.timeframe) ?? Timeframe.H1,
  initial_capital: values.initialCapital.trim(),
  fee_rate: nullable(values.feeRate),
  slippage_bps: values.slippageBps.trim(),
  risk: {
    max_position_fraction: values.maxPositionFraction.trim(),
    max_order_notional: nullable(values.maxOrderNotional),
    max_daily_loss_pct: nullable(values.maxDailyLossPct),
    max_drawdown_pct: nullable(values.maxDrawdownPct),
    max_consecutive_losses:
      values.maxConsecutiveLosses.trim() === ""
        ? null
        : Number.parseInt(values.maxConsecutiveLosses, 10),
    max_risk_per_trade_pct: nullable(values.maxRiskPerTradePct),
    min_liquidation_distance_pct:
      values.product === TradingProduct.LinearPerpetual
        ? nullable(values.minLiquidationDistancePct)
        : null,
    require_stop_loss: values.requireStopLoss,
    max_candle_range_pct: nullable(values.maxCandleRangePct),
    max_order_pct_of_volume: nullable(values.maxOrderPctOfVolume),
    max_close_jump_pct: nullable(values.maxCloseJumpPct),
    drawdown_action: values.drawdownAction,
  },
  mode: values.mode,
  connection_id:
    values.mode === ExecutionMode.Paper && values.product !== TradingProduct.LinearPerpetual
      ? null
      : nullable(values.connectionId),
});

export type FuturesEntryEstimate = {
  notional: string;
  collateral: string;
};

export const futuresEntryEstimate = (values: BotFormValues): FuturesEntryEstimate | null => {
  return estimateLeveragedEntry(
    values.initialCapital,
    values.maxPositionFraction,
    values.leverage,
    values.feeRate.trim() === "" ? "0.0005" : values.feeRate,
    values.maxOrderNotional.trim(),
  );
};
