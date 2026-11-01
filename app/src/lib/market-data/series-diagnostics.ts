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

export const sampleEveryValue = (text: string): number => {
  const parsed = Number.parseInt(text, 10);
  return Number.isFinite(parsed) && parsed >= 1 && parsed <= 1000 ? parsed : 1;
};
