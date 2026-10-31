import type { Bot, BotInput } from "@/lib/bots/bots.api";
import { ExecutionMode, Timeframe } from "@/lib/shared/enums";
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
  requireStopLoss: boolean;
  maxCandleRangePct: string;
  mode: string;
  connectionId: string;
};

export const defaultFormValues = (strategy: Strategy | undefined): BotFormValues => ({
  name: "",
  exchange: DEFAULT_EXCHANGE,
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
  requireStopLoss: false,
  maxCandleRangePct: "25",
  mode: ExecutionMode.Paper,
  connectionId: "",
});

const text = (value: string | number | null): string => (value === null ? "" : String(value));

export const formFromBot = (bot: Bot, strategy: Strategy | undefined): BotFormValues => ({
  name: bot.name,
  exchange: bot.exchange,
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
  requireStopLoss: bot.risk.require_stop_loss,
  maxCandleRangePct: text(bot.risk.max_candle_range_pct),
  mode: bot.mode,
  connectionId: bot.connection_id ?? "",
});

const nullable = (value: string): string | null => (value.trim() === "" ? null : value.trim());

export const toBotInput = (values: BotFormValues, strategy: Strategy | undefined): BotInput => ({
  name: values.name.trim(),
  exchange: values.exchange,
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
    require_stop_loss: values.requireStopLoss,
    max_candle_range_pct: nullable(values.maxCandleRangePct),
  },
  mode: values.mode,
  connection_id: values.mode === ExecutionMode.Paper ? null : nullable(values.connectionId),
});
