import type { Bot, DivergenceStepResult } from "@/lib/bots/bots.api";
import { formatInteger, formatRatio, formatSignedPercent } from "@/lib/shared/format";
import {
  DivergenceStep,
  FillTiming,
  ParityClass,
  StepState,
  TradingProduct,
  Unknown,
} from "@/lib/shared/enums";
import type { BacktestPrefill } from "@/lib/shared/backtest-prefill";

export const PARITY_CLASS_LABELS: Record<ParityClass | Unknown, string> = {
  [ParityClass.Match]: "Iguais",
  [ParityClass.Cost]: "Só o preço",
  [ParityClass.Risk]: "Risco decidiu diferente",
  [ParityClass.Operational]: "Motivo operacional",
  [ParityClass.Data]: "Candle ausente",
  [ParityClass.Unexplained]: "Não explicada",
  [Unknown]: "Desconhecida",
};

export const PARITY_CLASS_HELP: Record<ParityClass | Unknown, string> = {
  [ParityClass.Match]: "Mesmo sinal, mesma decisão, mesmo preço.",
  [ParityClass.Cost]: "Mesma operação com outro preço (slippage, preenchimento real).",
  [ParityClass.Risk]: "O risco de um lado recusou o que o outro aceitou.",
  [ParityClass.Operational]:
    "O bot recusou por algo que o backtest não tem: sinal atrasado, ordem pendente, kill switch, aviso de chave ou relógio.",
  [ParityClass.Data]: "O candle não foi guardado (ou era inválido): o replay não o viu.",
  [ParityClass.Unexplained]: "Nada explica a diferença: é o sinal de um bug.",
  [Unknown]: "",
};

export const STEP_LABELS: Record<DivergenceStep | Unknown, string> = {
  [DivergenceStep.Bugs]: "1. Bugs",
  [DivergenceStep.Trades]: "2. As operações batem com o backtest?",
  [DivergenceStep.Costs]: "3. Custo de execução",
  [DivergenceStep.Liquidity]: "4. Liquidez",
  [DivergenceStep.Snooping]: "5. Ajuste excessivo (data-snooping)",
  [DivergenceStep.Regime]: "6. Mudança de regime",
  [Unknown]: "Passo desconhecido",
};

export const STEP_STATE_LABELS: Record<StepState | Unknown, string> = {
  [StepState.Ok]: "Ok",
  [StepState.Attention]: "Atenção",
  [StepState.NoData]: "Sem dados",
  [Unknown]: "—",
};

export const backtestPrefillFromBot = (bot: Bot): BacktestPrefill => ({
  strategy: bot.strategy_type,
  product:
    bot.product === TradingProduct.Spot || bot.product === TradingProduct.LinearPerpetual
      ? bot.product
      : undefined,
  leverage: String(bot.leverage),
  allowShort: bot.allow_short,
  connectionId: bot.connection_id ?? "",
  symbol: bot.symbol,
  timeframe: bot.timeframe,
  params: JSON.stringify(bot.strategy_params),
  feeRate: bot.fee_rate,
  initialCapital: bot.initial_capital,
  slippageBps: bot.slippage_bps,
  fillTiming: FillTiming.SignalClose,
  risk: JSON.stringify(bot.risk),
});

const NO_DATA_TEXT: Record<DivergenceStep | Unknown, string> = {
  [DivergenceStep.Bugs]: "Rode a comparação com o backtest (aba Paridade).",
  [DivergenceStep.Trades]: "Rode a comparação com o backtest (aba Paridade).",
  [DivergenceStep.Costs]: "Ainda não há ordem executada com preço de referência.",
  [DivergenceStep.Liquidity]: "",
  [DivergenceStep.Snooping]:
    "Sem replay simplificado: o bot já usa os parâmetros padrão, ou a paridade não rodou.",
  [DivergenceStep.Regime]:
    "Sem backtest comparável (mesma estratégia, parâmetros, par e intervalo) com resultado por período.",
  [Unknown]: "",
};

const text = (value: string | number | null | undefined): string | null =>
  value === null || value === undefined ? null : String(value);

export const stepText = (step: DivergenceStepResult): string => {
  if (step.state === StepState.NoData) return NO_DATA_TEXT[step.key] || step.detail;
  const v = step.values ?? {};
  const n = (key: string): string => formatInteger(Number.parseInt(text(v[key]) ?? "0", 10));
  switch (step.key) {
    case DivergenceStep.Bugs:
      return `${n("unexplained")} diferença(s) sem explicação com o replay.`;
    case DivergenceStep.Trades:
      return `${n("match")} sinais iguais e ${n("explained")} diferença(s) explicada(s) (custo, risco, operacional ou dados).`;
    case DivergenceStep.Costs:
      return `Slippage medido de ${formatRatio(text(v["realized_bps"]))} bps contra ${formatRatio(text(v["assumed_bps"]))} bps assumidos nos backtests.`;
    case DivergenceStep.Liquidity:
      return `${n("refusals")} entrada(s) limitada(s) ou recusada(s) pelo limite de volume.`;
    case DivergenceStep.Snooping:
      return `Com os parâmetros afinados: ${formatSignedPercent(text(v["tuned_pct"]))}; com os parâmetros padrão nos mesmos candles: ${formatSignedPercent(text(v["default_pct"]))}. Se o resultado some sem a afinação, desconfie de ajuste ao ruído.`;
    case DivergenceStep.Regime:
      return `O bot fez ${formatSignedPercent(text(v["bot_pct"]))}; o pior período do backtest comparável fez ${formatSignedPercent(text(v["worst_period_pct"]))}.`;
    default:
      return step.detail;
  }
};
