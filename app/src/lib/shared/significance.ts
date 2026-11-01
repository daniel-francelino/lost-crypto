import type { Metrics } from "@/lib/shared/analytics";
import { compareDecimal, formatRatio } from "@/lib/shared/format";

type Significance = Pick<Metrics, "sharpe_t_stat" | "significance_p">;

export const SIGNIFICANCE_NOTE =
  "Teste gaussiano de Chan (um lado). Valor-p não é a chance de a estratégia funcionar; caudas pesadas e autocorrelação de cripto tornam o teste otimista.";

export const significanceValue = (metrics: Significance): string => {
  if (metrics.sharpe_t_stat === null || metrics.sharpe_t_stat === undefined) return "n/d";
  if (metrics.significance_p === null || metrics.significance_p === undefined) {
    return "não distinguível de acaso";
  }
  return `p < ${metrics.significance_p.replace(".", ",")}`;
};

export const significanceHint = (metrics: Significance): string =>
  metrics.sharpe_t_stat === null || metrics.sharpe_t_stat === undefined
    ? "Amostra curta ou resultado antigo."
    : `t = ${formatRatio(metrics.sharpe_t_stat)}. ${SIGNIFICANCE_NOTE}`;

export const belowFivePercent = (tStat: string | null | undefined, limit: string): boolean =>
  tStat !== null && tStat !== undefined && compareDecimal(tStat, limit) < 0;
