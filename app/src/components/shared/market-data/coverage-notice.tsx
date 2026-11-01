import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { useRangeCoverage, type RangeParams } from "@/hooks/shared/use-coverage";
import { dayEndUtcIso, dayStartUtcIso, formatUtc, formatUtcDay, toMs } from "@/lib/shared/dates";
import { formatDuration, formatInteger } from "@/lib/shared/format";
import type { Coverage, RangeCoverage } from "@/lib/shared/market-data/coverage.api";
import { gapsOverLimit, largestGapSeconds } from "@/lib/shared/market-data/gaps";

const largestGapStart = (range: RangeCoverage): string | null =>
  range.gaps.reduce<RangeCoverage["gaps"][number] | null>(
    (best, gap) => (best === null || gap.missing > best.missing ? gap : best),
    null,
  )?.start ?? null;

const rangeText = (range: RangeCoverage, timeframe: string): string => {
  const where = largestGapStart(range);
  const largest = formatDuration(largestGapSeconds(range, timeframe));
  return `Faltam ${formatInteger(range.missing)} de ${formatInteger(range.expected)} candles neste período; maior buraco: ${largest}${where === null ? "" : ` (a partir de ${formatUtc(where)})`}.`;
};

const isOutside = (coverage: Coverage, start: string, end: string): boolean =>
  coverage.first !== null &&
  coverage.last !== null &&
  (toMs(dayStartUtcIso(start)) < toMs(coverage.first) ||
    toMs(dayEndUtcIso(end)) > toMs(coverage.last));

export function CoverageNotice(params: RangeParams) {
  const query = useRangeCoverage(params);
  const coverage = query.data;
  if (coverage === undefined) return null;

  const empty = coverage.count === 0;
  const range = coverage.in_range ?? null;
  const missing = range !== null && range.missing > 0;
  const overLimit = gapsOverLimit(range, params.timeframe);
  const outside = range === null && !empty && isOutside(coverage, params.start, params.end);
  if (!empty && !missing && !outside) return null;

  return (
    <Alert className={overLimit || empty ? "border-destructive/50" : "border-warning/40"}>
      <AlertTitle>
        {empty
          ? "Sem dados de mercado para este par"
          : overLimit
            ? "Lacunas acima do limite neste período"
            : "Há lacunas neste período"}
      </AlertTitle>
      <AlertDescription>
        {empty
          ? "Não há candles salvos para este símbolo e intervalo. Importe os dados antes de rodar."
          : `Candles salvos: ${formatInteger(coverage.count)}, de ${formatUtcDay(coverage.first)} a ${formatUtcDay(coverage.last)}.`}
        {!empty && range === null && isOutside(coverage, params.start, params.end)
          ? " O período escolhido ultrapassa o que está salvo."
          : ""}
        {range !== null && missing ? ` ${rangeText(range, params.timeframe)}` : ""}
        {overLimit
          ? " Acima de 1% faltando ou de um buraco de 24 h o backtest é recusado, a menos que você marque “Rodar mesmo com lacunas”."
          : ""}
      </AlertDescription>
    </Alert>
  );
}
