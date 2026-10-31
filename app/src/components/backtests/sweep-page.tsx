import { Link } from "@tanstack/react-router";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { JobStatusBadge } from "@/components/shared/status/badges";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useSweep } from "@/hooks/backtests/use-backtests";
import type { SweepRun } from "@/lib/backtests/backtests.api";
import { compareDecimal, formatPercent, formatSignedPercent } from "@/lib/shared/format";

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
    id: "return",
    header: "Retorno (treino)",
    align: "right",
    sortable: true,
    accessor: (row) => row.total_return_pct,
    compare: (a, b) => compareDecimal(a.total_return_pct, b.total_return_pct),
    cell: (row) => (
      <SignedValue raw={row.total_return_pct} text={formatSignedPercent(row.total_return_pct)} />
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
      <Alert className="border-warning/40">
        <AlertTitle>Cuidado com o ajuste excessivo</AlertTitle>
        <AlertDescription>
          {sweep.note ||
            "Escolher o melhor resultado entre muitas combinações tende a superestimar o desempenho."}{" "}
          Compare sempre o retorno de treino com o de teste: a melhor combinação do treino pode não
          se repetir fora da amostra. Ranqueado por: {sweep.ranked_by}.
        </AlertDescription>
      </Alert>
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
