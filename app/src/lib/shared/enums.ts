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

export const Role = {
  Admin: "admin",
  Viewer: "viewer",
} as const;
export type Role = ValueOf<typeof Role>;

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

export const AlertKind = {
  WorkerDown: "worker_down",
  BotStale: "bot_stale",
  BotError: "bot_error",
  KillSwitchActive: "kill_switch_active",
  CandlesStale: "candles_stale",
  ExchangeRateLimited: "exchange_rate_limited",
} as const;
export type AlertKind = ValueOf<typeof AlertKind>;

export const AlertSeverity = {
  Warning: "warning",
  Critical: "critical",
} as const;
export type AlertSeverity = ValueOf<typeof AlertSeverity>;

export const Unknown = "unknown" as const;
export type Unknown = typeof Unknown;
