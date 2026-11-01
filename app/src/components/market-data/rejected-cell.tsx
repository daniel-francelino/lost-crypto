import type { ImportJob } from "@/lib/market-data/market-data.api";
import { formatUtc } from "@/lib/shared/dates";
import { formatInteger } from "@/lib/shared/format";
import { candleProblemsText } from "@/lib/shared/market-data/quality-labels";

export function RejectedCell({ job }: { job: ImportJob }) {
  const count = job.candles_rejected ?? 0;
  if (count === 0) return <span className="text-muted-foreground">0</span>;
  const samples = (job.rejection_samples ?? [])
    .map((sample) => `${formatUtc(sample.open_time)}: ${candleProblemsText(sample.problems)}`)
    .join("\n");
  return (
    <details className="text-right">
      <summary className="cursor-pointer font-medium text-warning">{formatInteger(count)}</summary>
      <p className="mt-1 whitespace-pre-line text-left text-xs text-muted-foreground">
        Não gravados:{"\n"}
        {samples}
      </p>
    </details>
  );
}
