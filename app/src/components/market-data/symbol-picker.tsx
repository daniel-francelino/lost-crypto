import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { useState } from "react";
import { DataTable, type DataTableColumn } from "lost-ui/data/data-table";
import { Badge } from "lost-ui/ui/badge";
import { Button } from "lost-ui/ui/button";
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

type SymbolPickerProps = { onAdded: () => void };

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

type RowToggle = (row: AvailableSymbol, active: boolean) => void;

function RowState({
  row,
  pendingId,
  onToggle,
}: {
  row: AvailableSymbol;
  pendingId: string | undefined;
  onToggle: RowToggle;
}) {
  if (row.registry_id === null) return null;
  return (
    <span className="flex items-center gap-2">
      <Badge variant="outline">Cadastrada</Badge>
      <Switch
        checked={row.active}
        disabled={pendingId === row.registry_id}
        onCheckedChange={(active) => onToggle(row, active)}
        aria-label={`${row.active ? "Desativar" : "Ativar"} ${displaySymbol(row.symbol)}`}
      />
    </span>
  );
}

export function SymbolPicker({ onAdded }: SymbolPickerProps) {
  const client = useQueryClient();
  const [exchange, setExchange] = useState<string>(ExchangeId.BinanceUsdm);
  const [sort, setSort] = useState<string>(AvailableSort.Volume);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
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
    mutationFn: (change: { id: string; active: boolean }) =>
      setRegisteredSymbolActive(change.id, change.active),
    onSuccess: async (updated) => {
      await client.invalidateQueries({ queryKey: QueryKey.Trends.all() });
      toast.success(updated.active ? "Moeda ativada." : "Moeda desativada.");
    },
    onError: (failure) => toast(errorMessage(failure)),
  });
  const onToggle: RowToggle = (row, active) => {
    if (row.registry_id !== null) toggle.mutate({ id: row.registry_id, active });
  };
  const pendingId = toggle.isPending ? toggle.variables?.id : undefined;
  const columns: DataTableColumn<AvailableSymbol>[] = [
    { id: "coin", header: "Moeda", cell: (row) => <PairIdentity row={row} /> },
    {
      id: "state",
      header: "",
      cell: (row) => <RowState row={row} pendingId={pendingId} onToggle={onToggle} />,
    },
  ];
  const add = useMutation({
    mutationFn: (symbols: readonly string[]) =>
      Promise.allSettled(symbols.map((symbol) => addRegisteredSymbol(exchange, symbol))),
    onSuccess: async (results) => {
      const refused = results.filter((item) => item.status === "rejected");
      const added = results.length - refused.length;
      await client.invalidateQueries({ queryKey: QueryKey.Trends.all() });
      setSelected([]);
      if (added > 0) {
        toast.success(`${added} moeda(s) cadastrada(s). O worker começa a calcular a tendência.`);
      }
      refused.forEach((item) => toast(errorMessage(item.reason)));
      if (added > 0) onAdded();
    },
    onError: (failure) => toast(errorMessage(failure)),
  });

  const changeExchange = (value: string) => {
    setExchange(value);
    setSelected([]);
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
          selectable
          selected={selected}
          onSelectedChange={setSelected}
          isRowSelectable={(row) => row.registry_id === null}
          selectionDisabledReason={(row) =>
            row.registry_id === null ? null : "Já cadastrada: use o switch"
          }
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
                <RowState row={row} pendingId={pendingId} onToggle={onToggle} />
              </span>
            </span>
          )}
          cardBreakpoint={ALWAYS_CARDS}
          empty={
            <Empty
              title="Nenhum par encontrado"
              description="Ajuste a busca. Só pares cotados em USDT são oferecidos."
            />
          }
        />
      )}
      <div className="flex shrink-0 items-center justify-between gap-3 border-t pt-3">
        <span className="text-xs text-muted-foreground">
          {total} par(es) · {selected.length} selecionada(s)
        </span>
        <Button
          disabled={selected.length === 0 || add.isPending}
          onClick={() => add.mutate(selected)}
        >
          {selected.length === 0 ? "Adicionar" : `Adicionar ${selected.length}`}
        </Button>
      </div>
    </div>
  );
}
