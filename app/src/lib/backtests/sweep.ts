import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { JobStatus, SweepRankBy, Unknown } from "@/lib/shared/enums";
import { compareDecimal, formatSignedPercent } from "@/lib/shared/format";

export const RANK_LABELS: Record<SweepRankBy | Unknown, string> = {
  [SweepRankBy.TotalReturn]: "retorno do período inteiro",
  [SweepRankBy.TrainReturn]: "retorno de treino",
  [SweepRankBy.TestReturn]: "retorno de teste",
  [SweepRankBy.Sharpe]: "Sharpe do período inteiro",
  [SweepRankBy.TrainSharpe]: "Sharpe de treino",
  [SweepRankBy.TestSharpe]: "Sharpe de teste",
  [Unknown]: "critério desconhecido",
};

export const RANK_NOTES: Record<SweepRankBy | Unknown, string> = {
  [SweepRankBy.TotalReturn]:
    "O período inteiro favorece parâmetros sobreajustados: use a fração fora da amostra para escolher no treino e conferir no teste.",
  [SweepRankBy.Sharpe]:
    "O período inteiro favorece parâmetros sobreajustados: use a fração fora da amostra para conferir o vencedor.",
  [SweepRankBy.TrainReturn]: "O treino escolhe; o teste só confere o vencedor.",
  [SweepRankBy.TrainSharpe]: "O treino escolhe; o teste só confere o vencedor.",
  [SweepRankBy.TestReturn]: "Escolher pelo teste o consome: ele deixa de ser fora da amostra.",
  [SweepRankBy.TestSharpe]: "Escolher pelo teste o consome: ele deixa de ser fora da amostra.",
  [Unknown]: "",
};

export type WinnerCheck = { winner: SweepRun; holds: boolean; reasons: string[] };

export const winnerCheck = (sweep: Sweep): WinnerCheck | null => {
  const winner = sweep.runs.find((run) => run.status === JobStatus.Completed);
  if (winner === undefined || winner.test_return_pct === null) return null;
  const testPositive = compareDecimal(winner.test_return_pct, "0") > 0;
  const beatsHolding = compareDecimal(winner.total_return_pct, winner.buy_and_hold_return_pct) >= 0;
  const reasons = [
    testPositive
      ? `positivo no teste (${formatSignedPercent(winner.test_return_pct)})`
      : `não lucrou no teste (${formatSignedPercent(winner.test_return_pct)})`,
    beatsHolding
      ? "rendeu ao menos o mesmo que comprar e segurar"
      : `rendeu menos que comprar e segurar (${formatSignedPercent(winner.buy_and_hold_return_pct)})`,
  ];
  return { winner, holds: testPositive && beatsHolding, reasons };
};
