import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { CalendarDays, Database } from "lucide-react";
import { PageHeader } from "lost-ui/app/page-header";
import { LineChart } from "lost-ui/charts/line-chart";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Empty } from "lost-ui/data/empty";
import { Form } from "lost-ui/forms/form";
import { FormInput } from "lost-ui/forms/form-input";
import { FormSelect } from "lost-ui/forms/form-select";
import { rules } from "lost-ui/forms/rules";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { ErrorBlock, QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { CoverageNotice } from "@/components/shared/market-data/coverage-notice";
import { IconCardTitle } from "@/components/shared/metrics/icon-card-title";
import { ListingStatusLine } from "@/components/market-data/listing-status";
import { OutliersCard } from "@/components/market-data/outliers-card";
import { HalfLifeCard } from "@/components/market-data/half-life-card";
import { MomentumGridCard } from "@/components/market-data/momentum-grid-card";
import { RegimeBreaksCard } from "@/components/market-data/regime-breaks-card";
import { BreaksWarning } from "@/components/shared/market-data/breaks-warning";
import { RejectedCell } from "@/components/market-data/rejected-cell";
import { JobStatusBadge } from "@/components/shared/status/badges";
import type { MarketDataSearch } from "@/lib/shared/market-data/search";
import { useSessionUser } from "@/hooks/shared/use-session";
import { useCapabilities } from "@/hooks/shared/use-system";
import { closeChartRows } from "@/lib/market-data/candle-chart-rows";
import {
  type ImportJob,
  listCandles,
  listImports,
  requestImport,
} from "@/lib/market-data/market-data.api";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";
import {
  dayEndUtcIso,
  dayStartUtcIso,
  daysAgoString,
  formatDateTime,
  formatUtcDay,
  isDayString,
} from "@/lib/shared/dates";
import { Timeframe } from "@/lib/shared/enums";
import { formatInteger } from "@/lib/shared/format";
import { Poll, isJobFinished } from "@/lib/shared/polling";

const IMPORT_LIMIT = 20;
const CANDLE_LIMIT = 500;
const TIMEFRAMES = Object.values(Timeframe).map((value) => ({ label: value, value }));
const SERIES = [{ key: "close", label: "Fechamento" }];

const importColumns: DataTableColumn<ImportJob>[] = [
  { id: "symbol", header: "Símbolo", accessor: "symbol" },
  { id: "timeframe", header: "Intervalo", accessor: "timeframe" },
  {
    id: "range",
    header: "Período (UTC)",
    cell: (row) => `${formatUtcDay(row.start)} → ${formatUtcDay(row.end)}`,
  },
  {
    id: "status",
    header: "Situação",
    accessor: "status",
    cell: (row) => <JobStatusBadge status={row.status} />,
  },
  {
    id: "count",
    header: "Candles",
    accessor: "candles_imported",
    align: "right",
    cell: (row) => formatInteger(row.candles_imported),
  },
  {
    id: "rejected",
    header: "Rejeitados",
    align: "right",
    cell: (row) => <RejectedCell job={row} />,
  },
  {
    id: "changed",
    header: "Alterados",
    align: "right",
    cell: (row) => formatInteger(row.candles_changed ?? 0),
  },
  {
    id: "created",
    header: "Criada em",
    accessor: "created_at",
    cell: (row) => formatDateTime(row.created_at),
  },
  { id: "error", header: "Erro", accessor: "error" },
];

export function MarketDataPage({ initial = {} }: { initial?: MarketDataSearch }) {
  const user = useSessionUser();
  const client = useQueryClient();
  const capabilities = useCapabilities();
  const exchanges = capabilities.data?.exchanges ?? ["binance"];
  const [exchange, setExchange] = useState("binance");
  const [symbol, setSymbol] = useState(initial.symbol ?? "BTC/USDT");
  const [timeframe, setTimeframe] = useState<string>(initial.timeframe ?? Timeframe.H1);
  const [start, setStart] = useState(initial.start ?? daysAgoString(30));
  const [end, setEnd] = useState(initial.end ?? daysAgoString(0));
  const [error, setError] = useState<string | null>(null);

  const imports = useQuery({
    queryKey: QueryKey.MarketData.imports(IMPORT_LIMIT),
    queryFn: ({ signal }) => listImports(IMPORT_LIMIT, signal),
    refetchInterval: (query) =>
      (query.state.data ?? []).some((job) => !isJobFinished(job.status)) ? Poll.Fast : false,
  });

  const validRange = isDayString(start) && isDayString(end) && start < end;
  const preview = useQuery({
    queryKey: QueryKey.MarketData.candles(exchange, symbol, timeframe, start, end),
    queryFn: ({ signal }) =>
      listCandles(
        {
          exchange,
          symbol,
          timeframe,
          start: dayStartUtcIso(start),
          end: dayEndUtcIso(end),
          limit: CANDLE_LIMIT,
        },
        signal,
      ),
    enabled: validRange && symbol !== "",
  });

  const importMutation = useMutation({
    mutationFn: () =>
      requestImport({
        exchange,
        symbol: symbol.trim().toUpperCase(),
        timeframe,
        start: dayStartUtcIso(start),
        end: dayEndUtcIso(end),
      }),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.MarketData.all() });
      toast("Importação na fila: o worker busca os candles na exchange.");
    },
    onError: (failure) => setError(errorMessage(failure)),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dados de mercado"
        description="Candles salvos, lacunas e importações. Datas e horas em UTC."
      />
      <Card>
        <CardHeader>
          <IconCardTitle className="text-base" icon={CalendarDays}>
            Par e período
          </IconCardTitle>
          <CardDescription>
            O mesmo recorte alimenta a cobertura, a prévia e a importação.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Form
            onSubmit={() => {
              setError(null);
              importMutation.mutate();
            }}
            className="space-y-4"
          >
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <FormSelect
                label="Exchange"
                items={exchanges.map((value) => ({ label: value, value }))}
                value={exchange}
                onValueChange={setExchange}
              />
              <FormInput
                label="Símbolo"
                value={symbol}
                onValueChange={setSymbol}
                rules={[rules.required("Informe o símbolo.")]}
              />
              <FormSelect
                label="Intervalo"
                items={TIMEFRAMES}
                value={timeframe}
                onValueChange={setTimeframe}
              />
              <FormInput
                label="De (UTC)"
                type="date"
                value={start}
                onValueChange={setStart}
                rules={[(value) => (isDayString(value ?? "") ? undefined : "Data inválida.")]}
              />
              <FormInput
                label="Até (UTC)"
                type="date"
                value={end}
                onValueChange={setEnd}
                rules={[
                  (value) => (isDayString(value ?? "") ? undefined : "Data inválida."),
                  () => (start <= end ? undefined : "O fim deve ser depois do início."),
                ]}
              />
            </div>
            {error === null ? null : (
              <p role="alert" className="text-sm text-destructive">
                {error}
              </p>
            )}
            {can(user, Capability.MarketDataImport) ? (
              <Button type="submit" disabled={importMutation.isPending}>
                {importMutation.isPending ? "Enviando…" : "Importar candles"}
              </Button>
            ) : null}
          </Form>
        </CardContent>
      </Card>

      {validRange ? (
        <CoverageNotice
          exchange={exchange}
          symbol={symbol}
          timeframe={timeframe}
          start={start}
          end={end}
        />
      ) : null}
      {symbol.trim() === "" ? null : (
        <ListingStatusLine exchange={exchange} symbol={symbol.trim().toUpperCase()} />
      )}

      <Card>
        <CardHeader>
          <IconCardTitle className="text-base" icon={Database}>
            Prévia do fechamento
          </IconCardTitle>
          <CardDescription>Até {CANDLE_LIMIT} candles do recorte; horários em UTC.</CardDescription>
        </CardHeader>
        <CardContent>
          <QueryBoundary query={preview}>
            {(candles) =>
              candles.length < 2 ? (
                <Empty
                  title="Sem candles neste recorte"
                  description="Importe os dados para ver o gráfico."
                />
              ) : (
                <figure className="space-y-2">
                  <LineChart
                    data={closeChartRows(candles)}
                    xKey="label"
                    series={SERIES}
                    className="h-64 w-full"
                  />
                  <figcaption className="text-xs text-muted-foreground">
                    {candles.length} candles de fechamento de {symbol} ({timeframe}).
                  </figcaption>
                </figure>
              )
            }
          </QueryBoundary>
        </CardContent>
      </Card>

      {validRange && symbol.trim() !== "" ? (
        <OutliersCard
          exchange={exchange}
          symbol={symbol.trim().toUpperCase()}
          timeframe={timeframe}
          start={start}
          end={end}
        />
      ) : null}
      {validRange && symbol.trim() !== "" ? (
        <BreaksWarning
          exchange={exchange}
          symbol={symbol.trim().toUpperCase()}
          start={start}
          end={end}
          onRestrict={(from, to) => {
            setStart(from);
            setEnd(to);
          }}
        />
      ) : null}
      {validRange && symbol.trim() !== "" ? (
        <HalfLifeCard
          exchange={exchange}
          symbol={symbol.trim().toUpperCase()}
          timeframe={timeframe}
          start={start}
          end={end}
        />
      ) : null}

      {validRange && symbol.trim() !== "" ? (
        <MomentumGridCard
          exchange={exchange}
          symbol={symbol.trim().toUpperCase()}
          timeframe={timeframe}
          start={start}
          end={end}
        />
      ) : null}
      <RegimeBreaksCard />

      <section className="space-y-3">
        <h2 className="text-base font-semibold">Importações</h2>
        {imports.isError && imports.data === undefined ? (
          <ErrorBlock error={imports.error} onRetry={() => void imports.refetch()} />
        ) : (
          <DataTable
            data={imports.data ?? []}
            columns={importColumns}
            getRowId={(row) => row.id}
            rowLabel={(row) => `${row.symbol} ${row.timeframe}`}
            caption="Importações de candles, mais recentes primeiro"
            loading={imports.isPending}
            empty={<Empty title="Nenhuma importação" />}
          />
        )}
      </section>
    </div>
  );
}
