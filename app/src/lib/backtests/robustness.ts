import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { RobustnessVerdict, SweepRankBy, type Unknown } from "@/lib/shared/enums";
import { formatFractionAsPercent, formatRatio, formatSignedPercent } from "@/lib/shared/format";

export type Robustness = NonNullable<Sweep["robustness"]>;

const isReturn = (metric: SweepRankBy | Unknown): boolean =>
  metric === SweepRankBy.TotalReturn ||
  metric === SweepRankBy.TrainReturn ||
  metric === SweepRankBy.TestReturn;

export const formatScore = (metric: SweepRankBy | Unknown, value: string | null): string =>
  isReturn(metric) ? formatSignedPercent(value) : formatRatio(value);

export const verdictText = (r: Robustness): string => {
  const ratio = formatFractionAsPercent(r.neighbour_ratio);
  if (r.verdict === RobustnessVerdict.Plateau) {
    return `Platô: os vizinhos do vencedor rendem ~${ratio} dele. Pequenas mudanças nos parâmetros não derrubam o resultado.`;
  }
  if (r.verdict === RobustnessVerdict.Peak) {
    return `Pico isolado: os vizinhos rendem só ~${ratio} do vencedor. Provável ajuste ao ruído; desconfie deste conjunto.`;
  }
  if (r.verdict === RobustnessVerdict.Unprofitable) {
    return "Nenhuma combinação deu lucro pelo critério do ranking: não há o que proteger.";
  }
  return "Grade pequena demais (ou poucos resultados) para dizer se é platô ou pico: use ao menos 3 valores por parâmetro.";
};

export type CrossTable = {
  rowName: string;
  columnName: string;
  rows: string[];
  columns: string[];
  cell: (row: string, column: string) => SweepRun | undefined;
};

const keyOf = (value: unknown): string => String(value);

export const crossTable = (sweep: Sweep): CrossTable | null => {
  const names = Object.keys(sweep.grid).sort();
  if (names.length !== 2) return null;
  const [rowName = "", columnName = ""] = names;
  const values = (name: string): string[] => {
    const raw = sweep.grid[name];
    return Array.isArray(raw) ? raw.map(keyOf) : [];
  };
  const index = new Map<string, SweepRun>();
  for (const run of sweep.runs) {
    index.set(
      `${keyOf(run.strategy_params[rowName])}|${keyOf(run.strategy_params[columnName])}`,
      run,
    );
  }
  return {
    rowName,
    columnName,
    rows: values(rowName),
    columns: values(columnName),
    cell: (row, column) => index.get(`${row}|${column}`),
  };
};

const SCORES: Record<SweepRankBy, (run: SweepRun) => string | null | undefined> = {
  [SweepRankBy.TotalReturn]: (run) => run.total_return_pct,
  [SweepRankBy.TrainReturn]: (run) => run.train_return_pct,
  [SweepRankBy.TestReturn]: (run) => run.test_return_pct,
  [SweepRankBy.Sharpe]: (run) => run.sharpe_ratio,
  [SweepRankBy.TrainSharpe]: (run) => run.train_sharpe_ratio,
  [SweepRankBy.TestSharpe]: (run) => run.test_sharpe_ratio,
};

export const scoreOf = (run: SweepRun, metric: SweepRankBy | Unknown): string | null =>
  metric in SCORES ? (SCORES[metric as SweepRankBy](run) ?? null) : null;
