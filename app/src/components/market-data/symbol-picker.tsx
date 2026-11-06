import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Badge } from "lost-ui/ui/badge";
import { Button } from "lost-ui/ui/button";
import { Checkbox } from "lost-ui/ui/checkbox";
import { Input } from "lost-ui/ui/input";
import { toast } from "lost-ui/ui/sonner";
import { Tabs, TabsList, TabsTrigger } from "lost-ui/ui/tabs";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { CoinIcon } from "@/components/shared/market-data/coin-icon";
import { useMarketCatalog } from "@/hooks/shared/use-market-catalog";
import { addRegisteredSymbol } from "@/lib/market-data/registry.api";
import { pickerView, toggleSelection } from "@/lib/market-data/symbol-picker";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { ExchangeId } from "@/lib/shared/enums";
import { exchangeLabel } from "@/lib/shared/labels";
import type { RegisteredSymbol } from "@/lib/shared/market-data/registry.api";

type SymbolPickerProps = { registered: readonly RegisteredSymbol[] };

export function SymbolPicker({ registered }: SymbolPickerProps) {
  const client = useQueryClient();
  const [exchange, setExchange] = useState<string>(ExchangeId.BinanceUsdm);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string[]>([]);
  const catalog = useMarketCatalog(exchange);
  const view = pickerView(catalog.data ?? [], registered, exchange, query);
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
    },
    onError: (failure) => toast(errorMessage(failure)),
  });

  const changeExchange = (value: string) => {
    setExchange(value);
    setSelected([]);
    setQuery("");
  };

  return (
    <div className="space-y-4">
      <Tabs value={exchange} onValueChange={changeExchange}>
        <TabsList>
          {Object.values(ExchangeId).map((item) => (
            <TabsTrigger key={item} value={item}>
              {exchangeLabel(item)}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>
      <div className="flex flex-wrap items-center gap-3">
        <Input
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar moeda (BTC, SOL…)"
          aria-label="Buscar moeda"
          className="max-w-xs"
        />
        <Button
          disabled={selected.length === 0 || add.isPending}
          onClick={() => add.mutate(selected)}
        >
          {selected.length === 0 ? "Adicionar" : `Adicionar ${selected.length} selecionada(s)`}
        </Button>
      </div>
      {catalog.isPending ? <SkeletonBlock rows={5} /> : null}
      {catalog.isError ? (
        <ErrorBlock error={catalog.error} onRetry={() => void catalog.refetch()} />
      ) : null}
      {catalog.isSuccess && view.rows.length === 0 ? (
        <Empty
          title="Nenhum par encontrado"
          description="Ajuste a busca. Só pares cotados em USDT são oferecidos."
        />
      ) : null}
      {view.rows.length > 0 ? (
        <>
          <ul className="grid gap-1 sm:grid-cols-2 lg:grid-cols-3">
            {view.rows.map((row) => (
              <li key={row.symbol}>
                <label className="flex cursor-pointer items-center gap-3 rounded-md px-2 py-1.5 hover:bg-muted">
                  <Checkbox
                    checked={row.registered || selected.includes(row.symbol)}
                    disabled={row.registered}
                    onCheckedChange={() => setSelected(toggleSelection(selected, row.symbol))}
                    aria-label={`Selecionar ${row.base}`}
                  />
                  <CoinIcon symbol={row.symbol} size={28} />
                  <span className="min-w-0">
                    <span className="block font-medium">{row.base}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {row.symbol}
                    </span>
                  </span>
                  {row.registered ? (
                    <Badge variant="outline" className="ml-auto">
                      Cadastrada
                    </Badge>
                  ) : null}
                </label>
              </li>
            ))}
          </ul>
          <p className="text-xs text-muted-foreground">
            Mostrando {view.rows.length} de {view.total} pares. Use a busca para achar os demais.
          </p>
        </>
      ) : null}
    </div>
  );
}
