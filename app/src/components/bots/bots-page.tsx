import { Link, useNavigate } from "@tanstack/react-router";
import { SymbolLabel } from "@/components/shared/market-data/coin-icon";
import { Plus } from "lucide-react";
import { useMemo, useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { FormSelect } from "lost-ui/forms/form-select";
import { Button } from "lost-ui/ui/button";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { BotStateBadge, ModeBadge } from "@/components/shared/status/badges";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useBots } from "@/hooks/bots/use-bots";
import { useOverview } from "@/hooks/shared/use-overview";
import { useSessionUser } from "@/hooks/shared/use-session";
import type { Bot, BotOverview } from "@/lib/bots/bots.api";
import { Capability, can } from "@/lib/shared/capability";
import { ageSeconds, formatAge } from "@/lib/shared/dates";
import { BotState, ExecutionMode } from "@/lib/shared/enums";
import { formatMoney, formatSignedPercent, quoteCurrency } from "@/lib/shared/format";
import { botStateLabel, modeLabel } from "@/lib/shared/labels";
import { AppRoute } from "@/lib/shared/routes";

type Row = { bot: Bot; overview: BotOverview | undefined };

const ALL = "all";
const STATE_ITEMS = [
  { label: "Todos os estados", value: ALL },
  ...Object.values(BotState).map((value) => ({ label: botStateLabel(value), value })),
];
const MODE_ITEMS = [
  { label: "Todos os modos", value: ALL },
  ...Object.values(ExecutionMode).map((value) => ({ label: modeLabel(value), value })),
];

const columns: DataTableColumn<Row>[] = [
  {
    id: "name",
    header: "Nome",
    accessor: (row) => row.bot.name,
    sortable: true,
    cell: (row) => (
      <Link
        to="/bots/$botId"
        params={{ botId: row.bot.id }}
        search={{}}
        className="font-medium underline-offset-4 hover:underline"
      >
        {row.bot.name}
      </Link>
    ),
  },
  {
    id: "symbol",
    header: "Par",
    accessor: (row) => row.bot.symbol,
    sortable: true,
    cell: (row) => <SymbolLabel symbol={row.bot.symbol} />,
  },
  { id: "timeframe", header: "Intervalo", accessor: (row) => row.bot.timeframe },
  { id: "strategy", header: "Estratégia", accessor: (row) => row.bot.strategy_type },
  {
    id: "mode",
    header: "Modo",
    accessor: (row) => row.bot.mode,
    cell: (row) => <ModeBadge mode={row.bot.mode} />,
  },
  {
    id: "state",
    header: "Estado",
    accessor: (row) => row.bot.observed_state,
    cell: (row) => <BotStateBadge state={row.bot.observed_state} />,
  },
  {
    id: "equity",
    header: "Capital",
    align: "right",
    cell: (row) => formatMoney(row.overview?.equity, quoteCurrency(row.bot.symbol)),
  },
  {
    id: "return",
    header: "Retorno",
    align: "right",
    cell: (row) => (
      <SignedValue
        raw={row.overview?.return_pct}
        text={formatSignedPercent(row.overview?.return_pct)}
      />
    ),
  },
  {
    id: "heartbeat",
    header: "Heartbeat",
    accessor: (row) => row.bot.last_heartbeat_at,
    cell: (row) => formatAge(ageSeconds(row.bot.last_heartbeat_at)),
  },
];

export function BotsPage() {
  const user = useSessionUser();
  const navigate = useNavigate();
  const bots = useBots();
  const overview = useOverview();
  const [state, setState] = useState(ALL);
  const [mode, setMode] = useState(ALL);

  const rows = useMemo<Row[]>(() => {
    const byId = new Map((overview.data ?? []).map((item) => [item.id, item]));
    return (bots.data ?? [])
      .filter((bot) => state === ALL || bot.observed_state === state)
      .filter((bot) => mode === ALL || bot.mode === mode)
      .map((bot) => ({ bot, overview: byId.get(bot.id) }));
  }, [bots.data, overview.data, state, mode]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Bots"
        description="Estratégias rodando em paper, testnet ou live."
        actions={
          can(user, Capability.BotsEdit) ? (
            <Button asChild className="gap-1.5">
              <Link to={AppRoute.BotsNew}>
                <Plus className="size-4" aria-hidden="true" />
                Novo bot
              </Link>
            </Button>
          ) : undefined
        }
      />
      <div className="flex flex-wrap gap-3">
        <FormSelect label="Estado" items={STATE_ITEMS} value={state} onValueChange={setState} />
        <FormSelect label="Modo" items={MODE_ITEMS} value={mode} onValueChange={setMode} />
      </div>
      {bots.isError && bots.data === undefined ? (
        <ErrorBlock error={bots.error} onRetry={() => void bots.refetch()} />
      ) : (
        <DataTable
          data={rows}
          columns={columns}
          getRowId={(row) => row.bot.id}
          rowLabel={(row) => row.bot.name}
          caption="Bots"
          loading={bots.isPending}
          searchable
          searchPlaceholder="Buscar bot"
          onRowClick={(row) =>
            void navigate({ to: "/bots/$botId", params: { botId: row.bot.id }, search: {} })
          }
          empty={
            <Empty
              title={
                bots.data?.length === 0 ? "Você ainda não tem bots" : "Nenhum bot com esses filtros"
              }
              description={
                bots.data?.length === 0 && can(user, Capability.BotsEdit)
                  ? "Crie o primeiro bot para começar em paper trading."
                  : undefined
              }
            />
          }
        />
      )}
    </div>
  );
}
