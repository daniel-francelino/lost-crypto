import { Link } from "@tanstack/react-router";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { RobustnessCard } from "@/components/backtests/robustness-card";
import { StartSensitivityCard } from "@/components/backtests/start-sensitivity-card";
import { JobStatusBadge } from "@/components/shared/status/badges";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useSweep } from "@/hooks/backtests/use-backtests";
import type { Sweep, SweepRun } from "@/lib/backtests/backtests.api";
import { RANK_LABELS, RANK_NOTES, winnerCheck } from "@/lib/backtests/sweep";
import {
  compareDecimal,
  formatInteger,
  formatPercent,
  formatRatio,
  formatSignedPercent,
} from "@/lib/shared/format";

const paramsText = (run: SweepRun): string =>
  Object.entries(run.strategy_params)
    .map(([name, value]) => `${name}=${String(value)}`)
    .join(", ");

const columns: DataTableColumn<SweepRun>[] = [
  {
    id: "params",
    header: "Parâmetros",
    cell: (row) => (
      <Link
        to="/backtests/$runId"
        params={{ runId: row.id }}
        className="font-medium underline-offset-4 hover:underline"
      >
        {paramsText(row)}
      </Link>
    ),
  },
  {
    id: "status",
    header: "Situação",
    accessor: "status",
    cell: (row) => <JobStatusBadge status={row.status} />,
  },
  {
    id: "train",
    header: "Retorno (treino)",
    align: "right",
    sortable: true,
    accessor: (row) => row.train_return_pct ?? null,
    compare: (a, b) => compareDecimal(a.train_return_pct ?? null, b.train_return_pct ?? null),
    cell: (row) => (
      <SignedValue raw={row.train_return_pct} text={formatSignedPercent(row.train_return_pct)} />
    ),
  },
  {
    id: "test",
    header: "Retorno (teste)",
    align: "right",
    cell: (row) => (
      <SignedValue raw={row.test_return_pct} text={formatSignedPercent(row.test_return_pct)} />
    ),
  },
  {
    id: "return",
    header: "Retorno (total)",
    align: "right",
    sortable: true,
    accessor: (row) => row.total_return_pct,
    compare: (a, b) => compareDecimal(a.total_return_pct, b.total_return_pct),
    cell: (row) => (
      <SignedValue raw={row.total_return_pct} text={formatSignedPercent(row.total_return_pct)} />
    ),
  },
  {
    id: "sharpe",
    header: "Sharpe (treino)",
    align: "right",
    sortable: true,
    accessor: (row) => row.train_sharpe_ratio ?? row.sharpe_ratio ?? null,
    compare: (a, b) =>
      compareDecimal(
        a.train_sharpe_ratio ?? a.sharpe_ratio ?? null,
        b.train_sharpe_ratio ?? b.sharpe_ratio ?? null,
      ),
    cell: (row) => formatRatio(row.train_sharpe_ratio ?? row.sharpe_ratio),
  },
  {
    id: "test-sharpe",
    header: "Sharpe (teste)",
    align: "right",
    cell: (row) => formatRatio(row.test_sharpe_ratio),
  },
  {
    id: "bh",
    header: "Comprar e segurar",
    align: "right",
    cell: (row) => formatSignedPercent(row.buy_and_hold_return_pct),
  },
  {
    id: "drawdown",
    header: "Drawdown",
    align: "right",
    cell: (row) => formatPercent(row.max_drawdown_pct),
  },
  { id: "trades", header: "Operações", align: "right", accessor: (row) => row.round_trips ?? 0 },
  { id: "error", header: "Erro", accessor: "error", defaultHidden: true },
];

function TrialsHeadline({ sweep }: { sweep: Sweep }) {
  const trials = sweep.trials ?? sweep.run_count + sweep.skipped.length;
  const prior = sweep.prior_trials ?? 0;
  return (
    <p className="text-lg font-semibold">
      Melhor de {formatInteger(trials)} tentativas
      {prior > 0 ? (
        <span className="font-normal text-muted-foreground">
          {" "}
          (mais ~{formatInteger(prior)} anteriores sobre estes dados)
        </span>
      ) : null}
    </p>
  );
}

function WinnerCheck({ sweep }: { sweep: Sweep }) {
  const check = winnerCheck(sweep);
  if (check === null) return null;
  return (
    <Alert variant={check.holds ? "default" : "destructive"}>
      <AlertTitle>
        {check.holds
          ? "O vencedor se manteve fora da amostra"
          : "O vencedor do treino não se sustentou fora da amostra"}
      </AlertTitle>
      <AlertDescription>
        {paramsText(check.winner)}: {check.reasons.join("; ")}.
      </AlertDescription>
    </Alert>
  );
}

export function SweepPage({ sweepId }: { sweepId: string }) {
  const query = useSweep(sweepId);
  const sweep = query.data;

  if (query.isError && sweep === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (sweep === undefined) return <SkeletonBlock rows={5} />;
  const running = sweep.completed + sweep.failed < sweep.run_count;

  return (
    <div className="space-y-6">
      <PageHeader
        title={`Varredura de ${sweep.strategy_type}`}
        description={`${sweep.completed} de ${sweep.run_count} concluídos${sweep.failed > 0 ? `, ${sweep.failed} com falha` : ""}.`}
      />
      <TrialsHeadline sweep={sweep} />
      <Alert className="border-warning/40">
        <AlertTitle>Cuidado com o ajuste excessivo</AlertTitle>
        <AlertDescription>
          Escolher o melhor entre muitas combinações superestima o desempenho dele. Ordenado por{" "}
          {RANK_LABELS[sweep.ranked_by]}. {RANK_NOTES[sweep.ranked_by]}
        </AlertDescription>
      </Alert>
      {running ? null : <WinnerCheck sweep={sweep} />}
      {running ? null : <StartSensitivityCard sweep={sweep} />}
      {running ? null : <RobustnessCard sweep={sweep} />}
      {running ? (
        <p className="text-sm text-muted-foreground">Em andamento; a tela atualiza sozinha.</p>
      ) : null}
      <DataTable
        data={sweep.runs}
        columns={columns}
        getRowId={(row) => row.id}
        rowLabel={paramsText}
        caption="Combinações da varredura"
        columnToggle
      />
      {sweep.skipped.length === 0 ? null : (
        <section className="space-y-1">
          <h2 className="text-base font-semibold">
            Combinações ignoradas ({sweep.skipped.length})
          </h2>
          <ul className="list-disc pl-5 text-sm text-muted-foreground">
            {sweep.skipped.map((item, index) => (
              <li key={index}>{JSON.stringify(item)}</li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
