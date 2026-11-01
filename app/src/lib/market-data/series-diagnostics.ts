import { compareDecimal, formatRatio } from "@/lib/shared/format";

const HURST_LOW = "0.45";
const HURST_HIGH = "0.55";
const RATIO_LOW = "0.9";
const RATIO_HIGH = "1.1";

export const hurstText = (hurst: string | null | undefined): string => {
  if (hurst === null || hurst === undefined) return "sem estimativa (série curta ou degenerada)";
  const value = formatRatio(hurst);
  if (compareDecimal(hurst, HURST_LOW) < 0) {
    return `H ≈ ${value}: tende a reverter`;
  }
  if (compareDecimal(hurst, HURST_HIGH) > 0) {
    return `H ≈ ${value}: tende a seguir tendência`;
  }
  return `H ≈ ${value}: parecido com passeio aleatório`;
};

export const varianceRatioText = (ratio: string, lag: number): string => {
  const value = formatRatio(ratio);
  if (compareDecimal(ratio, RATIO_LOW) < 0) {
    return `lag ${lag}: ${value} (abaixo de 1, tende a reverter)`;
  }
  if (compareDecimal(ratio, RATIO_HIGH) > 0) {
    return `lag ${lag}: ${value} (acima de 1, tende a seguir tendência)`;
  }
  return `lag ${lag}: ${value} (perto de 1, passeio aleatório)`;
};

const SUITABILITY_LAG = 8;
const HURST_NEUTRAL = "0.5";
const RATIO_NEUTRAL = "1";

export const TrendSuitability = {
  Favorable: "favorable",
  Unfavorable: "unfavorable",
  Inconclusive: "inconclusive",
} as const;
export type TrendSuitability = (typeof TrendSuitability)[keyof typeof TrendSuitability];

type RatioPoint = { lag: number; ratio: string };

export const trendSuitability = (
  hurst: string | null | undefined,
  ratios: readonly RatioPoint[] | undefined,
): TrendSuitability => {
  const long = (ratios ?? []).find((item) => item.lag === SUITABILITY_LAG);
  if (hurst === null || hurst === undefined || long === undefined) {
    return TrendSuitability.Inconclusive;
  }
  const persistent = compareDecimal(hurst, HURST_NEUTRAL) >= 0;
  const trending = compareDecimal(long.ratio, RATIO_NEUTRAL) >= 0;
  if (persistent && trending) return TrendSuitability.Favorable;
  if (!persistent && !trending) return TrendSuitability.Unfavorable;
  return TrendSuitability.Inconclusive;
};

export const trendSuitabilityText = (suitability: TrendSuitability): string => {
  if (suitability === TrendSuitability.Favorable) {
    return "Favorável a seguir tendência: persistência (Hurst ≥ 0,5) e razão de variâncias de 8 candles ≥ 1. Nos testes do projeto, pares assim tiveram resultado melhor, mas com poucos pares e correlação fraca; é um filtro de triagem, não uma garantia.";
  }
  if (suitability === TrendSuitability.Unfavorable) {
    return "Desfavorável a seguir tendência: Hurst < 0,5 e razão de variâncias de 8 candles < 1 apontam para reversão. Prefira uma estratégia de reversão ou outro par.";
  }
  return "Inconclusivo para tendência: os dois sinais discordam ou faltam dados. Não use este par com tendência sem validar fora da amostra.";
};

export const sampleEveryValue = (text: string): number => {
  const parsed = Number.parseInt(text, 10);
  return Number.isFinite(parsed) && parsed >= 1 && parsed <= 1000 ? parsed : 1;
};
