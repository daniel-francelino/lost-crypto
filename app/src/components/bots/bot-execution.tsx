import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { AlertTriangle, CheckCircle2, CircleDashed } from "lucide-react";
import { LineChart } from "lost-ui/charts/line-chart";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { toast } from "lost-ui/ui/sonner";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import { SideBadge } from "@/components/shared/status/badges";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useBotEquity, useDivergence, useExecutionQuality, useParity } from "@/hooks/bots/use-bots";
import { useSessionUser } from "@/hooks/shared/use-session";
import { type Bot, type ParitySummary, requestParity } from "@/lib/bots/bots.api";
import {
  PARITY_CLASS_HELP,
  PARITY_CLASS_LABELS,
  STEP_LABELS,
  STEP_STATE_LABELS,
  backtestPrefillFromBot,
  stepText,
} from "@/lib/bots/execution";
import { parityChartRows } from "@/lib/bots/parity-chart-rows";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";
import { formatDateTime, formatUtc } from "@/lib/shared/dates";
import { JobStatus, ParityClass, ParityVerdict, StepState } from "@/lib/shared/enums";
import { formatInteger, formatRatio, formatSignedPercent } from "@/lib/shared/format";
import { AppRoute } from "@/lib/shared/routes";

type Difference = ParitySummary["differences"][number];

const SERIES = [
  { key: "bot", label: "Bot" },
  { key: "replay", label: "Backtest (replay)" },
];

export function ExecutionQualityCard({ bot }: { bot: Bot }) {
  const query = useExecutionQuality(bot.id);
  const market = query.data?.by_type["market"];
  if (market === undefined || market.orders === 0) return null;
  const above = query.data?.above_configured === true;
  return (
    <Card className={above ? "border-warning/50" : undefined}>
      <CardHeader>
        <CardTitle className="text-base">Qualidade de execução</CardTitle>
        <CardDescription>
          Slippage medido entre o preço da decisão e o preço executado, contra o que os backtests
          assumem. Em paper ele é o próprio parâmetro; numa exchange é o custo real.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <StatTile
            label="Slippage médio"
            value={
              <span className={above ? "text-warning" : undefined}>
                {formatRatio(market.slippage_bps.mean)} bps
              </span>
            }
            hint={`Assumido: ${formatRatio(query.data?.configured_slippage_bps)} bps`}
          />
          <StatTile label="Pior slippage" value={`${formatRatio(market.slippage_bps.worst)} bps`} />
          <StatTile
            label="Latência média"
            value={
              market.latency_ms.mean === null ? "—" : `${formatInteger(market.latency_ms.mean)} ms`
            }
            hint={
              market.latency_ms.max === null
                ? undefined
                : `Máxima: ${formatInteger(market.latency_ms.max)} ms`
            }
          />
          <StatTile label="Ordens medidas" value={formatInteger(market.orders)} />
        </div>
        {above ? (
          <p className="text-sm">
            O custo real está acima do assumido. Rode os backtests com o slippage medido:{" "}
            <Link
              to={AppRoute.BacktestsNew}
              search={{
                ...backtestPrefillFromBot(bot),
                slippageBps: market.slippage_bps.mean ?? undefined,
              }}
              className="font-medium underline-offset-4 hover:underline"
            >
              backtest com {formatRatio(market.slippage_bps.mean)} bps
            </Link>
            .
          </p>
        ) : null}
      </CardContent>
    </Card>
  );
}

const differenceColumns: DataTableColumn<Difference>[] = [
  { id: "time", header: "Candle (UTC)", cell: (row) => formatUtc(row.bar_time) },
  { id: "side", header: "Lado", cell: (row) => <SideBadge side={row.side} /> },
  {
    id: "kind",
    header: "Classe",
    cell: (row) => (
      <span
        className={
          row.kind === ParityClass.Unexplained ? "font-medium text-destructive" : undefined
        }
        title={PARITY_CLASS_HELP[row.kind]}
      >
        {PARITY_CLASS_LABELS[row.kind]}
      </span>
    ),
  },
  { id: "bot", header: "Bot", accessor: "bot" },
  { id: "replay", header: "Backtest", accessor: "replay" },
];

function ParityResult({ summary, bot }: { summary: ParitySummary; bot: Bot }) {
  const equity = useBotEquity(bot.id);
  const consistent = summary.verdict === ParityVerdict.Consistent;
  const rows = parityChartRows(equity.data ?? [], summary);
  return (
    <div className="space-y-4">
      <Alert variant={consistent ? "default" : "destructive"}>
        <AlertTitle>
          {consistent
            ? "Consistente: nenhuma diferença sem explicação"
            : `${summary.counts[ParityClass.Unexplained] ?? 0} diferença(s) sem explicação`}
        </AlertTitle>
        <AlertDescription>
          Sessão {summary.session_mode} de {formatDateTime(summary.period_start)} a{" "}
          {formatDateTime(summary.period_end)}, {formatInteger(summary.candles)} candles guardados
          pelo bot, replay executando no fechamento do sinal e com os limites de risco do bot.
        </AlertDescription>
      </Alert>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        {Object.values(ParityClass).map((kind) => (
          <StatTile
            key={kind}
            label={PARITY_CLASS_LABELS[kind]}
            value={formatInteger(summary.counts[kind] ?? 0)}
            hint={PARITY_CLASS_HELP[kind]}
          />
        ))}
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatTile
          label="Retorno do bot"
          value={
            <SignedValue
              raw={summary.bot_return_pct}
              text={formatSignedPercent(summary.bot_return_pct)}
            />
          }
        />
        <StatTile
          label="Retorno do replay"
          value={
            <SignedValue
              raw={summary.replay_return_pct}
              text={formatSignedPercent(summary.replay_return_pct)}
            />
          }
        />
        <StatTile
          label="Replay com parâmetros padrão"
          value={formatSignedPercent(summary.simplified_return_pct)}
          hint="Checagem de ajuste excessivo: sem a afinação, o resultado se sustenta?"
        />
      </div>
      {rows.length < 2 ? null : (
        <figure className="space-y-2">
          <LineChart data={rows} xKey="label" series={SERIES} showLegend className="h-64 w-full" />
          <figcaption className="text-xs text-muted-foreground">
            Capital do bot e do replay no mesmo período. Quando são idênticos, as duas linhas ficam
            sobrepostas.
          </figcaption>
        </figure>
      )}
      <DataTable
        data={summary.differences}
        columns={differenceColumns}
        getRowId={(row, index) => `${row.bar_time}-${row.side}-${index}`}
        rowLabel={(row) => `${row.side} ${row.bar_time}`}
        caption="Diferenças entre o bot e o backtest (as iguais não aparecem)"
        pageSize={25}
        empty={<Empty title="Nenhuma diferença" description="Cada sinal teve o mesmo destino." />}
      />
    </div>
  );
}

export function ParityTab({ bot }: { bot: Bot }) {
  const user = useSessionUser();
  const client = useQueryClient();
  const query = useParity(bot.id);
  const mutation = useMutation({
    mutationFn: () => requestParity(bot.id),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.Bots.parity(bot.id) });
      toast("Comparação na fila: o worker refaz a sessão no backtester.");
    },
    onError: (failure) => toast(errorMessage(failure)),
  });
  const run = query.data;
  const busy =
    run !== null &&
    run !== undefined &&
    (run.status === JobStatus.Queued || run.status === JobStatus.Running);
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Paridade bot × backtest</CardTitle>
          <CardDescription>
            Refaz a última sessão do bot no backtester, com os mesmos candles, parâmetros, custos e
            limites de risco, e compara sinal a sinal (Chan, cap. 5: diferenças que os custos não
            explicam são bugs). Só leitura: não afeta o bot. O live exige uma comparação dos últimos
            7 dias sem diferenças sem explicação.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2">
          {can(user, Capability.BotsEdit) ? (
            <Button onClick={() => mutation.mutate()} disabled={mutation.isPending || busy}>
              {busy ? "Comparando…" : "Comparar com o backtest"}
            </Button>
          ) : null}
          <Button variant="outline" asChild>
            <Link to={AppRoute.BacktestsNew} search={backtestPrefillFromBot(bot)}>
              Rodar backtest com esta configuração
            </Link>
          </Button>
          {run ? (
            <span className="text-sm text-muted-foreground">
              Última: {formatDateTime(run.created_at)}
            </span>
          ) : null}
        </CardContent>
      </Card>
      {query.isError ? (
        <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
      ) : query.isPending ? (
        <SkeletonBlock rows={3} />
      ) : run === null || run === undefined ? (
        <Empty
          title="Nenhuma comparação ainda"
          description="Rode depois de alguns candles de paper."
        />
      ) : run.status === JobStatus.Failed ? (
        <Alert variant="destructive">
          <AlertTitle>A comparação falhou</AlertTitle>
          <AlertDescription>{run.error ?? "Sem detalhes."}</AlertDescription>
        </Alert>
      ) : run.summary === null ? (
        <p className="text-sm text-muted-foreground">O worker está comparando…</p>
      ) : (
        <ParityResult summary={run.summary} bot={bot} />
      )}
    </div>
  );
}

const STATE_ICON = {
  [StepState.Ok]: <CheckCircle2 className="size-4 text-success" aria-hidden="true" />,
  [StepState.Attention]: <AlertTriangle className="size-4 text-warning" aria-hidden="true" />,
  [StepState.NoData]: <CircleDashed className="size-4 text-muted-foreground" aria-hidden="true" />,
};

export function DiagnosisTab({ bot }: { bot: Bot }) {
  const query = useDivergence(bot.id);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Por que o resultado difere do backtest?</CardTitle>
        <CardDescription>
          A ordem de diagnóstico do livro (Chan, cap. 5). Má sorte nunca pode ser provada, então
          esta lista nunca conclui que foi azar.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {query.isError ? (
          <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />
        ) : query.data === undefined ? (
          <SkeletonBlock rows={6} />
        ) : (
          <ol className="space-y-3">
            {query.data.map((step) => (
              <li key={step.key} className="flex items-start gap-3 text-sm">
                <span className="mt-0.5">
                  {step.state in STATE_ICON ? STATE_ICON[step.state as StepState] : null}
                </span>
                <div>
                  <p className="font-medium">
                    {STEP_LABELS[step.key]} —{" "}
                    <span
                      className={
                        step.state === StepState.Attention
                          ? "text-warning"
                          : "text-muted-foreground"
                      }
                    >
                      {STEP_STATE_LABELS[step.state]}
                    </span>
                  </p>
                  <p className="text-muted-foreground">{stepText(step)}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
      </CardContent>
    </Card>
  );
}
