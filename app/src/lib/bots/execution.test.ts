import { describe, expect, it } from "vitest";
import type { Bot, ParitySummary } from "@/lib/bots/bots.api";
import {
  PARITY_CLASS_LABELS,
  STEP_LABELS,
  backtestPrefillFromBot,
  stepText,
} from "@/lib/bots/execution";
import { parityChartRows } from "@/lib/bots/parity-chart-rows";
import {
  BotState,
  DivergenceStep,
  ExecutionMode,
  FillTiming,
  ParityClass,
  ParityVerdict,
  StepState,
} from "@/lib/shared/enums";
import { parseJsonRecord } from "@/lib/shared/backtest-prefill";

const BOT: Bot = {
  id: "b",
  name: "bot",
  exchange: "binance",
  strategy_type: "ema_crossover",
  strategy_params: { fast_period: 9 },
  symbol: "BTC/USDT",
  product: "spot",
  leverage: 1,
  margin_mode: null,
  allow_short: false,
  timeframe: "1h",
  initial_capital: "1000",
  fee_rate: "0.001",
  slippage_bps: "5",
  risk: {
    max_position_fraction: "0.5",
    max_order_notional: null,
    max_daily_loss_pct: null,
    max_drawdown_pct: null,
    max_consecutive_losses: null,
    max_risk_per_trade_pct: null,
    require_stop_loss: true,
    max_candle_range_pct: null,
  },
  mode: ExecutionMode.Paper,
  connection_id: null,
  desired_state: BotState.Stopped,
  observed_state: BotState.Stopped,
  config_version: 1,
  live_approved: false,
  live_approved_at: null,
  last_heartbeat_at: null,
  last_error: null,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const SUMMARY: ParitySummary = {
  session_id: "s",
  session_mode: "paper",
  period_start: "2026-01-01T00:00:00Z",
  period_end: "2026-01-01T03:00:00Z",
  candles: 4,
  fill_timing: "signal_close",
  counts: {},
  verdict: ParityVerdict.Consistent,
  differences: [],
  bot_return_pct: "1",
  replay_return_pct: "1",
  simplified_return_pct: null,
  replay_equity: [
    ["2026-01-01T01:00:00Z", "1000"],
    ["2026-01-01T02:00:00Z", "1010"],
  ],
};

describe("execution systems helpers", () => {
  it("builds a backtest pre-fill that sizes and times like the bot", () => {
    const prefill = backtestPrefillFromBot(BOT);
    expect(prefill.fillTiming).toBe(FillTiming.SignalClose);
    expect(prefill.slippageBps).toBe("5");
    expect(parseJsonRecord(prefill.risk)).toMatchObject({
      max_position_fraction: "0.5",
      require_stop_loss: true,
    });
    expect(parseJsonRecord(prefill.params)).toEqual({ fast_period: 9 });
    expect(parseJsonRecord("not json")).toEqual({});

    const futuresPrefill = backtestPrefillFromBot({
      ...BOT,
      exchange: "binance-usdm",
      product: "linear_perpetual",
      leverage: 7,
      allow_short: true,
      connection_id: "demo-connection",
      symbol: "BTC/USDT:USDT",
      initial_capital: "2500",
    });
    expect(futuresPrefill).toMatchObject({
      product: "linear_perpetual",
      leverage: "7",
      allowShort: true,
      connectionId: "demo-connection",
      symbol: "BTC/USDT:USDT",
      initialCapital: "2500",
    });
  });

  it("puts the bot and the replay on one time axis, from the session start", () => {
    const rows = parityChartRows(
      [
        { time: "2025-12-31T23:00:00Z", equity: "990" },
        { time: "2026-01-01T01:00:00Z", equity: "1000" },
        { time: "2026-01-01T02:00:00Z", equity: "1009" },
      ],
      SUMMARY,
    );
    expect(rows.map((row) => [row.bot, row.replay])).toEqual([
      [1000, 1000],
      [1009, 1010],
    ]);
  });

  it("names every parity class and checklist step in Portuguese", () => {
    for (const kind of Object.values(ParityClass)) expect(PARITY_CLASS_LABELS[kind]).not.toBe("");
    for (const step of Object.values(DivergenceStep)) expect(STEP_LABELS[step]).not.toBe("");
  });

  it("writes each checklist step in Portuguese from the numbers", () => {
    expect(
      stepText({
        key: DivergenceStep.Costs,
        state: StepState.Ok,
        detail: "x",
        values: { realized_bps: "5.00", assumed_bps: "5.000000000000000000" },
      }),
    ).toBe("Slippage medido de 5,00 bps contra 5,00 bps assumidos nos backtests.");
    expect(
      stepText({ key: DivergenceStep.Regime, state: StepState.NoData, detail: "x", values: {} }),
    ).toContain("Sem backtest comparável");
    expect(
      stepText({
        key: DivergenceStep.Snooping,
        state: StepState.Attention,
        detail: "x",
        values: { tuned_pct: "12.5", default_pct: "-3" },
      }),
    ).toContain("+12,50%");
  });
});
