export type ValueOf<T> = T[keyof T];

export const BotState = {
  Stopped: "stopped",
  Running: "running",
  Paused: "paused",
  Error: "error",
} as const;
export type BotState = ValueOf<typeof BotState>;

export const ExecutionMode = {
  Paper: "paper",
  Testnet: "testnet",
  Live: "live",
} as const;
export type ExecutionMode = ValueOf<typeof ExecutionMode>;

export const TradingProduct = {
  Spot: "spot",
  LinearPerpetual: "linear_perpetual",
} as const;
export type TradingProduct = ValueOf<typeof TradingProduct>;

export const ExchangeId = {
  Binance: "binance",
  BinanceUsdm: "binance-usdm",
} as const;
export type ExchangeId = ValueOf<typeof ExchangeId>;

export const Trend = {
  Bullish: "bullish",
  Bearish: "bearish",
  Sideways: "sideways",
} as const;
export type Trend = ValueOf<typeof Trend>;

export const TrendFrame = {
  Week: "1w",
  Day: "1d",
  FourHours: "4h",
  Hour: "1h",
} as const;
export type TrendFrame = ValueOf<typeof TrendFrame>;

export const MarginMode = { Isolated: "isolated" } as const;
export type MarginMode = ValueOf<typeof MarginMode>;

export const Role = {
  Admin: "admin",
  Viewer: "viewer",
} as const;
export type Role = ValueOf<typeof Role>;

export const SweepRankBy = {
  TotalReturn: "total_return_pct",
  TrainReturn: "train_return_pct",
  TestReturn: "test_return_pct",
  Sharpe: "sharpe_ratio",
  TrainSharpe: "train_sharpe_ratio",
  TestSharpe: "test_sharpe_ratio",
} as const;
export type SweepRankBy = ValueOf<typeof SweepRankBy>;

export const BreakEvenStatus = {
  Found: "found",
  NeverProfitable: "never_profitable",
  AboveMax: "above_max",
} as const;
export type BreakEvenStatus = ValueOf<typeof BreakEvenStatus>;

export const PeriodGranularity = {
  Year: "year",
  Quarter: "quarter",
} as const;
export type PeriodGranularity = ValueOf<typeof PeriodGranularity>;

export const CandleProblem = {
  NonPositivePrice: "non_positive_price",
  NegativeVolume: "negative_volume",
  HighBelowBody: "high_below_body",
  LowAboveBody: "low_above_body",
  MisalignedTime: "misaligned_time",
} as const;
export type CandleProblem = ValueOf<typeof CandleProblem>;

export const ListingStatus = {
  Active: "active",
  Inactive: "inactive",
  Delisted: "delisted",
} as const;
export type ListingStatus = ValueOf<typeof ListingStatus>;

export const RobustnessVerdict = {
  Plateau: "plateau",
  Peak: "peak",
  Unprofitable: "unprofitable",
  Insufficient: "insufficient",
} as const;
export type RobustnessVerdict = ValueOf<typeof RobustnessVerdict>;

export const ParityClass = {
  Match: "match",
  Cost: "cost",
  Risk: "risk",
  Operational: "operational",
  Data: "data",
  Unexplained: "unexplained",
} as const;
export type ParityClass = ValueOf<typeof ParityClass>;

export const ParityVerdict = {
  Consistent: "consistent",
  Differences: "differences",
} as const;
export type ParityVerdict = ValueOf<typeof ParityVerdict>;

export const DivergenceStep = {
  Bugs: "bugs",
  Trades: "trades",
  Costs: "costs",
  Liquidity: "liquidity",
  Snooping: "snooping",
  Regime: "regime",
} as const;
export type DivergenceStep = ValueOf<typeof DivergenceStep>;

export const StepState = {
  Ok: "ok",
  Attention: "attention",
  NoData: "no_data",
} as const;
export type StepState = ValueOf<typeof StepState>;

export const FillTiming = {
  NextOpen: "next_open",
  SignalClose: "signal_close",
} as const;
export type FillTiming = ValueOf<typeof FillTiming>;

export const DrawdownAction = {
  Pause: "pause",
  Stop: "stop",
} as const;
export type DrawdownAction = ValueOf<typeof DrawdownAction>;

export const SlippageModel = {
  Fixed: "fixed",
  VolatilitySize: "volatility_size",
} as const;
export type SlippageModel = ValueOf<typeof SlippageModel>;

export const SizingScope = { Day: "day", Bar: "bar" } as const;
export type SizingScope = ValueOf<typeof SizingScope>;

export const SizingBinding = {
  HalfKelly: "half_kelly",
  TailStrategy: "tail_strategy",
  TailAsset: "tail_asset",
  SpotLimit: "spot_limit",
} as const;
export type SizingBinding = ValueOf<typeof SizingBinding>;

export const JobStatus = {
  Queued: "queued",
  Running: "running",
  Completed: "completed",
  Failed: "failed",
} as const;
export type JobStatus = ValueOf<typeof JobStatus>;

export const ConnectionStatus = {
  Active: "active",
  Disabled: "disabled",
  Invalid: "invalid",
  Pending: "pending",
} as const;
export type ConnectionStatus = ValueOf<typeof ConnectionStatus>;

export const Environment = {
  Demo: "demo",
  Testnet: "testnet",
  Live: "live",
} as const;
export type Environment = ValueOf<typeof Environment>;

export const Timeframe = {
  M1: "1m",
  M5: "5m",
  M15: "15m",
  H1: "1h",
  H4: "4h",
  D1: "1d",
} as const;
export type Timeframe = ValueOf<typeof Timeframe>;

export const OrderStatus = {
  Intent: "INTENT",
  Submitting: "SUBMITTING",
  Open: "OPEN",
  PartiallyFilled: "PARTIALLY_FILLED",
  Filled: "FILLED",
  Canceled: "CANCELED",
  Rejected: "REJECTED",
  Expired: "EXPIRED",
  Unknown: "UNKNOWN",
} as const;
export type OrderStatus = ValueOf<typeof OrderStatus>;

export const Side = {
  Buy: "buy",
  Sell: "sell",
} as const;
export type Side = ValueOf<typeof Side>;

export const SignalKind = {
  Entry: "entry",
  Exit: "exit",
} as const;
export type SignalKind = ValueOf<typeof SignalKind>;

export const StrategyStyle = {
  Trend: "trend",
  MeanReversion: "mean_reversion",
} as const;
export type StrategyStyle = ValueOf<typeof StrategyStyle>;

export const AlertKind = {
  WorkerDown: "worker_down",
  BotStale: "bot_stale",
  BotError: "bot_error",
  KillSwitchActive: "kill_switch_active",
  CandlesStale: "candles_stale",
  ExchangeRateLimited: "exchange_rate_limited",
  PerformanceDegraded: "performance_degraded",
  ProtectiveExitSlippage: "protective_exit_slippage",
  FuturesUnprotectedPosition: "futures_unprotected_position",
  FuturesMarkStale: "futures_mark_stale",
  FuturesMarginBuffer: "futures_margin_buffer",
  FuturesRecoveryRequired: "futures_recovery_required",
  FuturesFundingCost: "futures_funding_cost",
} as const;
export type AlertKind = ValueOf<typeof AlertKind>;

export const AlertSeverity = {
  Warning: "warning",
  Critical: "critical",
} as const;
export type AlertSeverity = ValueOf<typeof AlertSeverity>;

export const Unknown = "unknown" as const;
export type Unknown = typeof Unknown;
