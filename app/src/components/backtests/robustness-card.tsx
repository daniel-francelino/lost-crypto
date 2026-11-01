import { Link } from "@tanstack/react-router";
import { Trophy } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import type { Sweep } from "@/lib/backtests/backtests.api";
import {
  type CrossTable,
  type Robustness,
  crossTable,
  formatScore,
  scoreOf,
  verdictText,
} from "@/lib/backtests/robustness";
import { RANK_LABELS } from "@/lib/backtests/sweep";
import { RobustnessVerdict } from "@/lib/shared/enums";
import { Sign, formatPercent, signOf } from "@/lib/shared/format";

const TONE: Record<string, string> = {
  [Sign.Positive]: "bg-success/10",
  [Sign.Negative]: "bg-destructive/10",
};

function Cross({ table, sweep, winnerId }: { table: CrossTable; sweep: Sweep; winnerId: string }) {
  const metric = sweep.ranked_by;
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-max border-collapse text-sm tabular-nums">
        <caption className="pb-2 text-left text-xs text-muted-foreground">
          {RANK_LABELS[metric]} por combinação ({table.rowName} nas linhas, {table.columnName} nas
          colunas). A cor só reforça o sinal escrito.
        </caption>
        <thead>
          <tr>
            <th scope="col" className="p-2 text-left font-medium text-muted-foreground">
              {table.rowName} \ {table.columnName}
            </th>
            {table.columns.map((column) => (
              <th key={column} scope="col" className="p-2 text-right font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row) => (
            <tr key={row} className="border-t">
              <th scope="row" className="p-2 text-left font-medium">
                {row}
              </th>
              {table.columns.map((column) => {
                const run = table.cell(row, column);
                const value = run === undefined ? null : scoreOf(run, metric);
                return (
                  <td key={column} className={`p-2 text-right ${TONE[signOf(value)] ?? ""}`}>
                    {run === undefined ? (
                      <span className="text-muted-foreground">—</span>
                    ) : (
                      <Link
                        to="/backtests/$runId"
                        params={{ runId: run.id }}
                        className="inline-flex items-center gap-1 underline-offset-4 hover:underline"
                      >
                        {run.id === winnerId ? (
                          <Trophy className="size-3" aria-label="vencedor" />
                        ) : null}
                        {formatScore(metric, value)}
                      </Link>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Summary({ robustness, metric }: { robustness: Robustness; metric: Sweep["ranked_by"] }) {
  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm sm:grid-cols-4">
      <dt className="text-muted-foreground">Vencedor</dt>
      <dd>{formatScore(metric, robustness.winner_score)}</dd>
      <dt className="text-muted-foreground">Média dos {robustness.neighbours} vizinhos</dt>
      <dd>{formatScore(metric, robustness.neighbour_mean)}</dd>
      <dt className="text-muted-foreground">Média do top 3</dt>
      <dd>{formatScore(metric, robustness.top3_mean)}</dd>
      <dt className="text-muted-foreground">Combinações lucrativas</dt>
      <dd>{formatPercent(robustness.profitable_share)}</dd>
    </dl>
  );
}

export function RobustnessCard({ sweep }: { sweep: Sweep }) {
  const robustness = sweep.robustness;
  if (robustness === null || robustness === undefined) return null;
  const table = crossTable(sweep);
  const winner = sweep.runs[0];
  const warn =
    robustness.verdict === RobustnessVerdict.Peak ||
    robustness.verdict === RobustnessVerdict.Unprofitable;
  return (
    <Card className={warn ? "border-warning/50" : undefined}>
      <CardHeader>
        <CardTitle className="text-base">Robustez: platô ou pico?</CardTitle>
        <CardDescription>
          Um bom parâmetro continua bom quando você o muda um pouco (Chan, cap. 3). Em vez de
          apostar no melhor, considere a média do top 3.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className={warn ? "font-medium text-warning" : "font-medium"}>
          {verdictText(robustness)}
        </p>
        <Summary robustness={robustness} metric={sweep.ranked_by} />
        {table === null || winner === undefined ? null : (
          <Cross table={table} sweep={sweep} winnerId={winner.id} />
        )}
      </CardContent>
    </Card>
  );
}
