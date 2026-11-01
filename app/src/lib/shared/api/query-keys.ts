export const QueryKey = {
  Auth: {
    all: () => ["auth"] as const,
    users: () => ["auth", "users"] as const,
  },
  Bots: {
    all: () => ["bots"] as const,
    list: () => ["bots", "list"] as const,
    summary: () => ["bots", "summary"] as const,
    overview: () => ["bots", "overview"] as const,
    interventions: (id: string, days: number) => ["bots", id, "interventions", days] as const,
    detail: (id: string) => ["bots", "detail", id] as const,
    portfolio: (id: string) => ["bots", id, "portfolio"] as const,
    performance: (id: string) => ["bots", id, "performance"] as const,
    equity: (id: string, limit: number) => ["bots", id, "equity", limit] as const,
    orders: (id: string, limit: number, offset: number) =>
      ["bots", id, "orders", limit, offset] as const,
    signals: (id: string, limit: number, offset: number) =>
      ["bots", id, "signals", limit, offset] as const,
    readiness: (id: string) => ["bots", id, "live-readiness"] as const,
    executionQuality: (id: string) => ["bots", id, "execution-quality"] as const,
    parity: (id: string) => ["bots", id, "parity"] as const,
    backtestComparison: (id: string, runId: string) =>
      ["bots", id, "backtest-comparison", runId] as const,
    divergence: (id: string) => ["bots", id, "divergence"] as const,
  },
  Backtests: {
    all: () => ["backtests"] as const,
    list: (limit: number, offset: number) => ["backtests", "list", limit, offset] as const,
    detail: (id: string) => ["backtests", "detail", id] as const,
    trades: (id: string) => ["backtests", id, "trades"] as const,
    equity: (id: string) => ["backtests", id, "equity"] as const,
    sizing: (id: string, tolerable: string, scope: string) =>
      ["backtests", id, "sizing", tolerable, scope] as const,
    compare: (ids: string[]) => ["backtests", "compare", ...ids] as const,
    sweep: (id: string) => ["backtests", "sweep", id] as const,
  },
  MarketData: {
    all: () => ["market-data"] as const,
    coverage: (exchange: string, symbol: string, timeframe: string, start = "", end = "") =>
      ["market-data", "coverage", exchange, symbol, timeframe, start, end] as const,
    outliers: (exchange: string, symbol: string, timeframe: string, start: string, end: string) =>
      ["market-data", "outliers", exchange, symbol, timeframe, start, end] as const,
    halfLife: (
      exchange: string,
      symbol: string,
      timeframe: string,
      start: string,
      end: string,
      sampleEvery = 1,
    ) =>
      ["market-data", "half-life", exchange, symbol, timeframe, start, end, sampleEvery] as const,
    listings: (exchange: string, symbol: string) =>
      ["market-data", "listings", exchange, symbol] as const,
    imports: (limit: number) => ["market-data", "imports", limit] as const,
    candles: (exchange: string, symbol: string, timeframe: string, start: string, end: string) =>
      ["market-data", "candles", exchange, symbol, timeframe, start, end] as const,
  },
  Strategies: { all: () => ["strategies"] as const },
  Exchanges: { connections: () => ["exchange-connections"] as const },
  System: {
    all: () => ["system"] as const,
    status: () => ["system", "status"] as const,
    capabilities: () => ["system", "capabilities"] as const,
    killSwitch: () => ["system", "kill-switch"] as const,
  },
  Alerts: {
    all: () => ["alerts"] as const,
    summary: () => ["alerts", "summary"] as const,
    list: (unreadOnly: boolean, severity: string | null, limit: number, offset: number) =>
      ["alerts", "list", unreadOnly, severity, limit, offset] as const,
  },
  Audit: {
    list: (botId: string | null, eventType: string | null, limit: number, offset: number) =>
      ["audit", botId, eventType, limit, offset] as const,
  },
} as const;
