import type { MomentumGrid } from "@/lib/market-data/market-data.api";
import { formatRatio } from "@/lib/shared/format";

export const DEFAULT_LAGS = "1, 5, 10, 25";
export const MAX_CELLS = 100;

export type LagList = { values: number[]; error: string | null };

export const parseLags = (text: string): LagList => {
  const parts = text
    .split(",")
    .map((part) => part.trim())
    .filter((part) => part !== "");
  const values = parts.map((part) => Number.parseInt(part, 10));
  if (values.length === 0) return { values: [], error: "Informe ao menos um valor." };
  if (parts.some((part) => !/^\d+$/.test(part)) || values.some((value) => value < 1)) {
    return { values: [], error: "Use inteiros a partir de 1, separados por vírgula." };
  }
  return { values, error: null };
};

export const gridError = (lookbacks: LagList, holdings: LagList): string | null =>
  lookbacks.error ??
  holdings.error ??
  (lookbacks.values.length * holdings.values.length > MAX_CELLS
    ? `São ${lookbacks.values.length * holdings.values.length} células; o máximo é ${MAX_CELLS}.`
    : null);

type Cell = MomentumGrid["cells"][number];

export const cellText = (cell: Cell): string => {
  if (cell.correlation === null || cell.correlation === undefined) return "—";
  const verdict =
    cell.significant_corrected === true ? "passa a 5% com correção" : "não passa a 5% com correção";
  return `r = ${formatRatio(cell.correlation)} · n = ${cell.n} · ${verdict}`;
};

export const lookbacksOf = (grid: MomentumGrid): number[] => [
  ...new Set(grid.cells.map((cell) => cell.lookback)),
];

export const holdingsOf = (grid: MomentumGrid): number[] => [
  ...new Set(grid.cells.map((cell) => cell.holding)),
];

export const cellAt = (grid: MomentumGrid, lookback: number, holding: number): Cell | undefined =>
  grid.cells.find((cell) => cell.lookback === lookback && cell.holding === holding);
