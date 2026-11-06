import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Switch } from "lost-ui/ui/switch";
import { toast } from "lost-ui/ui/sonner";
import { Tabs, TabsList, TabsTrigger } from "lost-ui/ui/tabs";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { CoinIcon } from "@/components/shared/market-data/coin-icon";
import {
  type AvailableSymbol,
  addRegisteredSymbol,
  listAvailableSymbols,
  setRegisteredSymbolActive,
} from "@/lib/market-data/registry.api";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { AvailableSort, ExchangeId } from "@/lib/shared/enums";
import { availableSortLabel, exchangeLabel } from "@/lib/shared/labels";
import { formatCompactMoney } from "@/lib/shared/format";
import { displaySymbol } from "@/lib/shared/market-data/coins";

const QUOTE = "USDT";
const SEARCH_DEBOUNCE_MS = 300;
const STALE_MS = 60_000;
const ALWAYS_CARDS = Number.MAX_SAFE_INTEGER;

type Change = { row: AvailableSymbol; active: boolean };

function PairIdentity({ row }: { row: AvailableSymbol }) {
  return (
    <span className="flex min-w-0 items-center gap-3">
      <CoinIcon symbol={row.symbol} size={36} />
      <span className="min-w-0">
        <span className="block font-medium">{row.base}</span>
        <span className="block truncate text-xs text-muted-foreground">
          {displaySymbol(row.symbol)} · volume 24 h {formatCompactMoney(row.quote_volume, QUOTE)}
        </span>
      </span>
    </span>
  );
}

type PairSwitchProps = {
  row: AvailableSymbol;
  pending: boolean;
  onToggle: (change: Change) => void;
};

function PairSwitch({ row, pending, onToggle }: PairSwitchProps) {
  return (
    <Switch
      checked={row.active}
      disabled={pending}
      onCheckedChange={(active) => onToggle({ row, active })}
      aria-label={`${row.active ? "Desativar" : "Ativar"} ${displaySymbol(row.symbol)}`}
    />
  );
}

export function SymbolPicker() {
  const client = useQueryClient();
  const [exchange, setExchange] = useState<string>(ExchangeId.BinanceUsdm);
  const [sort, setSort] = useState<string>(AvailableSort.Volume);
  const [query, setQuery] = useState("");
  const available = useInfiniteQuery({
    queryKey: QueryKey.Trends.available(exchange, query, sort),
    queryFn: ({ pageParam, signal }) =>
      listAvailableSymbols(exchange, query, sort, pageParam, signal),
    initialPageParam: 0,
    getNextPageParam: (last, pages) => {
      const loaded = pages.reduce((count, page) => count + page.items.length, 0);
      return loaded < last.total ? loaded : undefined;
    },
    placeholderData: keepPreviousData,
    staleTime: STALE_MS,
  });
  const rows = available.data?.pages.flatMap((page) => page.items) ?? [];
  const total = available.data?.pages[0]?.total ?? 0;
  const toggle = useMutation({
    mutationFn: ({ row, active }: Change) =>
      row.registry_id === null
        ? addRegisteredSymbol(exchange, row.symbol)
        : setRegisteredSymbolActive(row.registry_id, active),
    onSuccess: async (updated) => {
      await client.invalidateQueries({ queryKey: QueryKey.Trends.all() });
      toast.success(updated.active ? "Moeda ativada." : "Moeda desativada.");
    },
    onError: (failure) => toast(errorMessage(failure)),
  });
  const pendingSymbol = toggle.isPending ? toggle.variables?.row.symbol : undefined;
  const columns: DataTableColumn<AvailableSymbol>[] = [
    { id: "coin", header: "Moeda", cell: (row) => <PairIdentity row={row} /> },
    {
      id: "active",
      header: "",
      cell: (row) => (
        <PairSwitch row={row} pending={pendingSymbol === row.symbol} onToggle={toggle.mutate} />
      ),
    },
  ];

  const changeExchange = (value: string) => {
    setExchange(value);
    setQuery("");
  };

  return (
    <div className="flex h-[calc(100dvh-11rem)] flex-col gap-3">
      <div className="flex shrink-0 flex-wrap items-center justify-between gap-3">
        <Tabs value={exchange} onValueChange={changeExchange}>
          <TabsList>
            {Object.values(ExchangeId).map((item) => (
              <TabsTrigger key={item} value={item}>
                {exchangeLabel(item)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Tabs value={sort} onValueChange={setSort}>
          <TabsList>
            {Object.values(AvailableSort).map((item) => (
              <TabsTrigger key={item} value={item}>
                {availableSortLabel(item)}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
      </div>
      {available.isError && rows.length === 0 ? (
        <ErrorBlock error={available.error} onRetry={() => void available.refetch()} />
      ) : (
        <DataTable
          key={exchange}
          className="min-h-0 flex-1"
          sticky
          data={rows}
          columns={columns}
          getRowId={(row) => row.symbol}
          rowLabel={(row) => row.base}
          caption="Pares da Binance"
          searchable
          manualSearch
          searchDebounce={SEARCH_DEBOUNCE_MS}
          searchPlaceholder="Buscar moeda (BTC, SOL…)"
          onSearchChange={setQuery}
          paginationMode="infinite"
          hasMore={available.hasNextPage}
          onLoadMore={() => void available.fetchNextPage()}
          loadingMore={available.isFetchingNextPage}
          loading={available.isPending}
          refreshing={available.isPlaceholderData}
          renderCard={(row) => (
            <span className="flex items-center gap-3">
              <PairIdentity row={row} />
              <span className="ml-auto">
                <PairSwitch
                  row={row}
                  pending={pendingSymbol === row.symbol}
                  onToggle={toggle.mutate}
                />
              </span>
            </span>
          )}
          cardBreakpoint={ALWAYS_CARDS}
          empty={
            <Empty
              title="Nenhum par encontrado"
              description="Ajuste a busca. Só pares de cripto cotados em USDT são oferecidos."
            />
          }
        />
      )}
      <p className="shrink-0 border-t pt-3 text-xs text-muted-foreground">{total} par(es)</p>
    </div>
  );
}
