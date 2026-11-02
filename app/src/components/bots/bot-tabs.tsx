import { BacktestComparisonCard } from "@/components/bots/backtest-comparison-card";
import type { ReactNode } from "react";
import { useState } from "react";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Card, CardContent, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { ErrorBlock, QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { MetricsGrid } from "@/components/shared/metrics/metrics-grid";
import { EquityChart } from "@/components/shared/metrics/equity-chart";
import { UnderwaterChart } from "@/components/shared/metrics/underwater-chart";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import { OrderStatusBadge, SideBadge } from "@/components/shared/status/badges";
import { SymbolLabel } from "@/components/shared/market-data/coin-icon";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useConnections } from "@/hooks/shared/use-catalog";
import {
  useBotEquity,
  useOrders,
  usePerformance,
  usePortfolio,
  useSignals,
} from "@/hooks/bots/use-bots";
import type { Bot, Order, Signal } from "@/lib/bots/bots.api";
import { formatDateTime, formatUtcShort } from "@/lib/shared/dates";
import { DrawdownAction, ExecutionMode } from "@/lib/shared/enums";
import { ExecutionQualityCard } from "@/components/bots/bot-execution";
import {
  compareDecimal,
  formatInteger,
  formatRatio,
  formatMoney,
  formatPrice,
  formatQuantity,
  formatSignedMoney,
  quoteCurrency,
  shortId,
} from "@/lib/shared/format";
import { drawdownActionLabel, signalKindLabel } from "@/lib/shared/labels";

const PAGE_SIZE = 25;
const DECISION_LABELS: Record<string, string> = {
  approved: "Aprovado",
  rejected: "Rejeitado",
  discarded_stale: "Descartado (atrasado)",
};

const usesExchange = (mode: string): boolean =>
  mode === ExecutionMode.Testnet || mode === ExecutionMode.Live;

function ConnectionWarning({ bot }: { bot: Bot }) {
  const connections = useConnections();
  const connection = connections.data?.find((item) => item.id === bot.connection_id);
  if (connection === undefined || !connection.permission_warning) return null;
  return (
    <Alert variant="destructive">
      <AlertTitle>Novas entradas bloqueadas: a chave “{connection.label}” mudou</AlertTitle>
      <AlertDescription>
        <p className="font-mono text-xs">{connection.permission_warning}</p>
        <p>
          Saídas e stops continuam funcionando. Corrija a chave na exchange e verifique de novo em
          Conexões.
        </p>
      </AlertDescription>
    </Alert>
  );
}

export function SummaryTab({ bot }: { bot: Bot }) {
  const portfolio = usePortfolio(bot.id);
  const equity = useBotEquity(bot.id);
  const quote = quoteCurrency(bot.symbol);

  return (
    <div className="space-y-4">
      <ConnectionWarning bot={bot} />
      <ExecutionQualityCard bot={bot} />
      {portfolio.data !== undefined &&
      usesExchange(bot.mode) &&
      compareDecimal(portfolio.data.quantity, "0") > 0 &&
      !portfolio.data.native_stop_active ? (
        <Alert className="border-warning/50">
          <AlertTitle>Sem stop na exchange — exposto se o worker cair</AlertTitle>
          <AlertDescription>
            Esta posição não tem stop guardado na exchange. Enquanto o worker estiver no ar ele
            vigia o stop; numa queda do servidor, nada protege a posição.
          </AlertDescription>
        </Alert>
      ) : null}
      <QueryBoundary query={portfolio}>
        {(data) => (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            <StatTile label="Capital (equity)" value={formatMoney(data.equity, quote)} />
            <StatTile
              label="Caixa"
              value={formatMoney(data.cash, quote)}
              hint={`Reservado: ${formatMoney(data.reserved_cash, quote)}`}
            />
            <StatTile
              label="Posição"
              value={formatQuantity(data.quantity)}
              hint={`Preço médio: ${formatPrice(data.avg_entry_price)}`}
            />
            <StatTile label="Último preço" value={formatPrice(data.last_price)} />
            <StatTile
              label="Resultado não realizado"
              value={
                <SignedValue
                  raw={data.unrealized_pnl}
                  text={formatSignedMoney(data.unrealized_pnl, quote)}
                />
              }
            />
            <StatTile
              label="Resultado realizado"
              value={
                <SignedValue
                  raw={data.realized_pnl}
                  text={formatSignedMoney(data.realized_pnl, quote)}
                />
              }
            />
            <StatTile label="Taxas pagas" value={formatMoney(data.fees_paid, quote)} />
            <StatTile
              label="Stop / alvo"
              value={`${formatPrice(data.stop_price)} / ${formatPrice(data.take_profit_price)}`}
              hint={data.native_stop_active ? "Stop nativo ativo na exchange" : "Sem stop nativo"}
            />
          </div>
        )}
      </QueryBoundary>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Curva de capital</CardTitle>
        </CardHeader>
        <CardContent>
          <QueryBoundary query={equity}>
            {(points) => (
              <div className="space-y-4">
                <EquityChart
                  points={points}
                  summary={`Últimos ${points.length} pontos de capital (horários em fuso local).`}
                />
                <UnderwaterChart points={points} />
              </div>
            )}
          </QueryBoundary>
        </CardContent>
      </Card>
    </div>
  );
}

export function OrdersTab({ bot }: { bot: Bot }) {
  const [page, setPage] = useState(1);
  const query = useOrders(bot.id, PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const columns: DataTableColumn<Order>[] = [
    {
      id: "time",
      header: "Quando",
      accessor: "created_at",
      cell: (row) => formatDateTime(row.created_at),
    },
    { id: "side", header: "Lado", accessor: "side", cell: (row) => <SideBadge side={row.side} /> },
    {
      id: "intent",
      header: "Intenção",
      accessor: "product",
      cell: (row) =>
        row.product === "linear_perpetual" ? (
          <div>
            <div>
              {row.reduce_only ? "Reduz" : "Abre"} {row.position_side ?? "posição"}
            </div>
            <div className="text-xs text-muted-foreground">
              {row.reduce_only ? "Reduce-only" : `${row.leverage}x`}
            </div>
          </div>
        ) : (
          "Spot"
        ),
    },
    { id: "type", header: "Tipo", accessor: "order_type" },
    {
      id: "qty",
      header: "Quantidade",
      accessor: "quantity",
      align: "right",
      cell: (row) => formatQuantity(row.quantity),
    },
    {
      id: "filled",
      header: "Executado",
      accessor: "filled_quantity",
      align: "right",
      cell: (row) => formatQuantity(row.filled_quantity),
    },
    {
      id: "price",
      header: "Preço médio",
      accessor: "avg_fill_price",
      align: "right",
      cell: (row) => formatPrice(row.avg_fill_price),
    },
    {
      id: "reference",
      header: "Referência",
      align: "right",
      cell: (row) => formatPrice(row.reference_price),
    },
    {
      id: "slippage",
      header: "Slippage (bps)",
      align: "right",
      cell: (row) => (
        <span
          className={
            compareDecimal(row.slippage_bps ?? null, bot.slippage_bps) > 0
              ? "font-medium text-warning"
              : undefined
          }
        >
          {formatRatio(row.slippage_bps)}
        </span>
      ),
    },
    {
      id: "latency",
      header: "Latência",
      align: "right",
      cell: (row) =>
        row.latency_ms === null || row.latency_ms === undefined
          ? "—"
          : `${formatInteger(row.latency_ms)} ms`,
    },
    {
      id: "status",
      header: "Situação",
      accessor: "status",
      cell: (row) => <OrderStatusBadge status={row.status} />,
    },
    {
      id: "client",
      header: "ID",
      accessor: "client_order_id",
      cell: (row) => (
        <code className="text-xs" title={row.client_order_id}>
          {shortId(row.client_order_id)}
        </code>
      ),
    },
    { id: "reason", header: "Motivo da rejeição", accessor: "reject_reason", defaultHidden: true },
  ];
  if (query.isError && query.data === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  return (
    <DataTable
      data={query.data?.data ?? []}
      columns={columns}
      getRowId={(row) => row.id}
      rowLabel={(row) => row.client_order_id}
      caption="Ordens do bot, mais recentes primeiro"
      loading={query.isPending}
      page={page}
      pageSize={PAGE_SIZE}
      total={query.data?.total ?? 0}
      onPageChange={setPage}
      columnToggle
      empty={<Empty title="Sem ordens" description="Este bot ainda não enviou ordens." />}
    />
  );
}

export function SignalsTab({ bot }: { bot: Bot }) {
  const [page, setPage] = useState(1);
  const query = useSignals(bot.id, PAGE_SIZE, (page - 1) * PAGE_SIZE);
  const columns: DataTableColumn<Signal>[] = [
    {
      id: "bar",
      header: "Candle (UTC)",
      accessor: "bar_time",
      cell: (row) => formatUtcShort(row.bar_time),
    },
    { id: "side", header: "Lado", accessor: "side", cell: (row) => <SideBadge side={row.side} /> },
    { id: "kind", header: "Tipo", accessor: "kind", cell: (row) => signalKindLabel(row.kind) },
    { id: "reason", header: "Motivo da estratégia", accessor: "reason" },
    {
      id: "decision",
      header: "Decisão do risco",
      accessor: "decision",
      cell: (row) => (
        <span>
          {DECISION_LABELS[row.decision] ?? row.decision}
          {row.decision_reason === null ? "" : ` — ${row.decision_reason}`}
        </span>
      ),
    },
  ];
  if (query.isError && query.data === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  return (
    <DataTable
      data={query.data?.data ?? []}
      columns={columns}
      getRowId={(row, index) => `${row.bar_time}-${row.kind}-${index}`}
      rowLabel={(row) => row.reason}
      caption="Sinais da estratégia e a decisão do risco"
      loading={query.isPending}
      page={page}
      pageSize={PAGE_SIZE}
      total={query.data?.total ?? 0}
      onPageChange={setPage}
      empty={<Empty title="Sem sinais" description="A estratégia ainda não gerou sinais." />}
    />
  );
}

export function PerformanceTab({ bot }: { bot: Bot }) {
  const query = usePerformance(bot.id);
  return (
    <div className="space-y-6">
      <QueryBoundary query={query}>
        {(metrics) =>
          metrics === null ? (
            <Empty
              title="Sem dados ainda"
              description="O desempenho aparece depois dos primeiros candles."
            />
          ) : (
            <MetricsGrid metrics={metrics} quote={quoteCurrency(bot.symbol)} />
          )
        }
      </QueryBoundary>
      <BacktestComparisonCard bot={bot} />
    </div>
  );
}

const orDash = (value: string | number | null): string => (value === null ? "—" : String(value));

export function ConfigTab({ bot }: { bot: Bot }) {
  const risk = bot.risk;
  const rows: [string, ReactNode][] = [
    ["Exchange", bot.exchange],
    ["Símbolo", <SymbolLabel symbol={bot.symbol} size={18} />],
    ["Intervalo", bot.timeframe],
    ["Estratégia", bot.strategy_type],
    ["Capital inicial", formatMoney(bot.initial_capital, quoteCurrency(bot.symbol))],
    ["Taxa (fração do valor)", bot.fee_rate],
    ["Slippage (bps)", bot.slippage_bps],
    ["Versão da configuração", String(bot.config_version)],
    ["Fração máxima por posição", risk.max_position_fraction],
    ["Valor máximo por ordem", orDash(risk.max_order_notional)],
    ["Perda diária máxima (%)", orDash(risk.max_daily_loss_pct)],
    ["Drawdown máximo (%)", orDash(risk.max_drawdown_pct)],
    ["Perdas consecutivas máximas", orDash(risk.max_consecutive_losses)],
    ["Risco máximo por operação (%)", orDash(risk.max_risk_per_trade_pct)],
    ["Exigir stop-loss", risk.require_stop_loss ? "Sim" : "Não"],
    ["Amplitude máxima do candle (%)", orDash(risk.max_candle_range_pct)],
    ["Salto máximo do fechamento (%)", orDash(risk.max_close_jump_pct ?? null)],
    [
      "Ao atingir o drawdown máximo",
      drawdownActionLabel(risk.drawdown_action ?? DrawdownAction.Pause),
    ],
  ];
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Configuração e limites</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 text-sm">
            {rows.map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-muted-foreground">{label}</dt>
                <dd className="text-right tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Parâmetros da estratégia</CardTitle>
        </CardHeader>
        <CardContent>
          <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2 text-sm">
            {Object.entries(bot.strategy_params).map(([name, value]) => (
              <div key={name} className="contents">
                <dt className="text-muted-foreground">{name}</dt>
                <dd className="text-right tabular-nums">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </CardContent>
      </Card>
    </div>
  );
}
