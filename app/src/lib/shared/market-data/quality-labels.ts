import { CandleProblem, type Unknown } from "@/lib/shared/enums";

const LABELS: Record<CandleProblem, string> = {
  [CandleProblem.NonPositivePrice]: "preço zero ou negativo",
  [CandleProblem.NegativeVolume]: "volume negativo",
  [CandleProblem.HighBelowBody]: "máxima abaixo da abertura/fechamento",
  [CandleProblem.LowAboveBody]: "mínima acima da abertura/fechamento",
  [CandleProblem.MisalignedTime]: "horário fora da grade do intervalo",
};

export const candleProblemLabel = (problem: CandleProblem | Unknown): string =>
  problem in LABELS ? LABELS[problem as CandleProblem] : "problema desconhecido";

export const candleProblemsText = (problems: (CandleProblem | Unknown)[]): string =>
  problems.map(candleProblemLabel).join(", ");
