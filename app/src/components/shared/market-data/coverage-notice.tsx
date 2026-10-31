import { useQuery } from "@tanstack/react-query";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { dayEndUtcIso, dayStartUtcIso, formatUtcDay, toMs } from "@/lib/shared/dates";
import { formatInteger } from "@/lib/shared/format";
import { type CoverageParams, getCoverage } from "@/lib/shared/market-data/coverage.api";

type CoverageNoticeProps = CoverageParams & { start: string; end: string };

export function CoverageNotice({ exchange, symbol, timeframe, start, end }: CoverageNoticeProps) {
  const query = useQuery({
    queryKey: QueryKey.MarketData.coverage(exchange, symbol, timeframe),
    queryFn: ({ signal }) => getCoverage({ exchange, symbol, timeframe }, signal),
    enabled: symbol !== "",
  });
  const coverage = query.data;
  if (coverage === undefined) return null;

  const empty = coverage.count === 0;
  const outside =
    !empty &&
    coverage.first !== null &&
    coverage.last !== null &&
    (toMs(dayStartUtcIso(start)) < toMs(coverage.first) ||
      toMs(dayEndUtcIso(end)) > toMs(coverage.last));
  const gaps = coverage.gaps.length;
  if (!empty && !outside && gaps === 0) return null;

  return (
    <Alert className="border-warning/40 text-warning">
      <AlertTitle>Dados de mercado incompletos para este par</AlertTitle>
      <AlertDescription>
        {empty
          ? "Não há candles salvos para este símbolo e intervalo. Importe os dados antes de rodar."
          : `Candles salvos: ${formatInteger(coverage.count)}, de ${formatUtcDay(coverage.first)} a ${formatUtcDay(coverage.last)}.`}
        {outside ? " O período escolhido ultrapassa o que está salvo." : ""}
        {gaps > 0 ? ` Há ${gaps} lacuna(s) nos dados.` : ""}
      </AlertDescription>
    </Alert>
  );
}
