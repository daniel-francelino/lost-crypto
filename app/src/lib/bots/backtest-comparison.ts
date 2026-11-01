import type { RealizedVsBacktest } from "@/lib/bots/bots.api";
import { compareDecimal, formatRatio } from "@/lib/shared/format";

export const ComparisonVerdict = {
  Unavailable: "unavailable",
  Below: "below",
  Acceptable: "acceptable",
} as const;
export type ComparisonVerdict = (typeof ComparisonVerdict)[keyof typeof ComparisonVerdict];

export const verdictOf = (comparison: RealizedVsBacktest): ComparisonVerdict => {
  if (comparison.ratio === null) return ComparisonVerdict.Unavailable;
  return compareDecimal(comparison.ratio, comparison.chan_min_ratio) < 0
    ? ComparisonVerdict.Below
    : ComparisonVerdict.Acceptable;
};

const REASONS: Record<string, string> = {
  "short live sample: no realized Sharpe yet":
    "Amostra real ainda curta: o Sharpe real só é calculado com mais retornos.",
  "the backtest has no Sharpe": "O backtest não tem Sharpe (amostra curta).",
  "the backtest Sharpe is not positive":
    "O Sharpe do backtest não é positivo: não há razão a calcular.",
  "no completed backtest with this bot's configuration":
    "Nenhum backtest concluído com a configuração deste bot.",
};

export const reasonText = (reason: string | null): string | null =>
  reason === null ? null : (REASONS[reason] ?? reason);

export const verdictText = (comparison: RealizedVsBacktest): string => {
  const verdict = verdictOf(comparison);
  if (verdict === ComparisonVerdict.Unavailable) {
    return reasonText(comparison.reason) ?? "Sem comparação disponível.";
  }
  const ratio = formatRatio(comparison.ratio);
  const minimum = formatRatio(comparison.chan_min_ratio);
  return verdict === ComparisonVerdict.Below
    ? `Sharpe real é ${ratio}× o do backtest, abaixo de ${minimum}×. Observação de Chan, não norma: a maioria se contenta com pelo menos metade.`
    : `Sharpe real é ${ratio}× o do backtest, acima de ${minimum}×. Amostra real curta é ruidosa: confira o número de retornos.`;
};
