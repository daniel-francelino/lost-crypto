import type { TrendReading } from "@/lib/shared/market-data/registry.api";

const CHECK_LABELS: Record<string, string> = {
  distance: "Distância entre as EMAs",
  slope: "Inclinação da EMA lenta",
  adx: "Força da tendência (ADX)",
  structure: "Topos e fundos",
};

const CHECK_ORDER = ["distance", "slope", "adx", "structure"];

export type CheckRow = { label: string; text: string };

export const checkText = (value: boolean | null | undefined): string => {
  if (value === true) return "Passou";
  if (value === false) return "Não passou";
  return "Sem dados ainda";
};

export const checkRows = (reading: TrendReading): CheckRow[] =>
  CHECK_ORDER.filter((key) => key in reading.checks).map((key) => ({
    label: CHECK_LABELS[key] ?? key,
    text: checkText(reading.checks[key]),
  }));
