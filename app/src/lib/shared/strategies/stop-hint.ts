import { StrategyStyle } from "@/lib/shared/enums";
import type { ParamValues } from "@/lib/shared/strategies/params";

const filled = (values: ParamValues, name: string): boolean => (values[name] ?? "").trim() !== "";

const SHORT_STOP =
  "Um stop curto numa reversão à média sai no pior momento, quando o desvio é maior. O livro põe o stop além da pior excursão histórica, só contra cisne negro; prefira o teto de risco.";
const NO_TIME_LIMIT =
  "Sem limite de tempo, uma posição que não reverte fica aberta indefinidamente; considere preencher o máximo de candles na posição.";
const TREND_WITHOUT_STOP =
  "Em estratégia de tendência a saída é o sinal oposto; um stop limita a perda quando o preço dá um salto.";

const meanReversionHints = (values: ParamValues): string[] => [
  ...(filled(values, "stop_loss_pct") ? [SHORT_STOP] : []),
  ...(values["max_holding_candles"] !== undefined && !filled(values, "max_holding_candles")
    ? [NO_TIME_LIMIT]
    : []),
];

const trendHints = (values: ParamValues): string[] =>
  values["stop_loss_pct"] !== undefined && !filled(values, "stop_loss_pct")
    ? [TREND_WITHOUT_STOP]
    : [];

export const stopHints = (style: string | undefined, values: ParamValues): string[] => {
  if (style === StrategyStyle.MeanReversion) return meanReversionHints(values);
  if (style === StrategyStyle.Trend) return trendHints(values);
  return [];
};
