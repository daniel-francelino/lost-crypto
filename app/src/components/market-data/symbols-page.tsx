import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Coins, Plus } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { Slideover } from "lost-ui/elements/slideover";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Skeleton } from "lost-ui/ui/skeleton";
import { toast } from "lost-ui/ui/sonner";
import { CoinCard } from "@/components/market-data/coin-card";
import { SymbolPicker } from "@/components/market-data/symbol-picker";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { ErrorBlock } from "@/components/shared/feedback/query-boundary";
import { UpdatedAt } from "@/components/shared/feedback/updated-at";
import { useSessionUser } from "@/hooks/shared/use-session";
import { useRegisteredSymbols, useTrends } from "@/hooks/shared/use-symbol-registry";
import { setRegisteredSymbolActive } from "@/lib/market-data/registry.api";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";

const SKELETON_CARDS = 3;

export function SymbolsPage() {
  const user = useSessionUser();
  const client = useQueryClient();
  const symbols = useRegisteredSymbols();
  const trends = useTrends();
  const [adding, setAdding] = useState(false);
  const manage = can(user, Capability.SymbolsManage);
  const trendsById = new Map((trends.data ?? []).map((item) => [item.symbol.id, item]));
  const toggle = useMutation({
    mutationFn: (change: { id: string; active: boolean }) =>
      setRegisteredSymbolActive(change.id, change.active),
    onSuccess: async (updated) => {
      await client.invalidateQueries({ queryKey: QueryKey.Trends.all() });
      toast.success(updated.active ? "Moeda ativada." : "Moeda desativada.");
    },
    onError: (failure) => toast(errorMessage(failure)),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <span className="inline-flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Coins className="size-5" aria-hidden="true" />
            </span>
            Moedas
          </span>
        }
        description="Moedas que o sistema acompanha."
        actions={
          <div className="flex items-center gap-3">
            <UpdatedAt updatedAtMs={trends.dataUpdatedAt} failed={trends.isError} />
            {manage ? (
              <Button className="gap-1.5" onClick={() => setAdding(true)}>
                <Plus className="size-4" aria-hidden="true" />
                Adicionar
              </Button>
            ) : null}
          </div>
        }
      />
      <p className="-mt-3 text-sm text-muted-foreground">
        Bots, backtests e importações de candles só aceitam as moedas cadastradas aqui. A tendência
        é calculada a cada fechamento de candle.
      </p>
      {symbols.isError && symbols.data === undefined ? (
        <ErrorBlock error={symbols.error} onRetry={() => void symbols.refetch()} />
      ) : null}
      {symbols.isPending ? (
        <div className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3" aria-busy="true">
          {Array.from({ length: SKELETON_CARDS }, (_, index) => (
            <Skeleton key={index} className="h-36 w-full" />
          ))}
        </div>
      ) : null}
      {symbols.data?.length === 0 ? (
        <Empty
          title="Nenhuma moeda cadastrada"
          description={
            manage
              ? "Use o botão Adicionar para escolher pares da Binance e liberar bots, backtests e importações."
              : "Um administrador precisa cadastrar as moedas para liberar bots, backtests e importações."
          }
        />
      ) : null}
      {symbols.data !== undefined && symbols.data.length > 0 ? (
        <ul className="grid gap-4 md:grid-cols-2 2xl:grid-cols-3" aria-label="Moedas cadastradas">
          {symbols.data.map((item) => (
            <li key={item.id}>
              <CoinCard
                item={item}
                trends={trendsById.get(item.id)}
                canManage={manage}
                pending={toggle.isPending && toggle.variables?.id === item.id}
                onToggle={(active) => toggle.mutate({ id: item.id, active })}
              />
            </li>
          ))}
        </ul>
      ) : null}
      {manage ? null : (
        <Alert>
          <AlertTitle>Somente leitura</AlertTitle>
          <AlertDescription>
            Somente administradores cadastram ou desativam moedas.
          </AlertDescription>
        </Alert>
      )}
      <Slideover
        open={adding}
        onOpenChange={setAdding}
        title="Adicionar moedas"
        description="A lista vem direto da Binance, das mais negociadas para as menos. Role para carregar mais."
        className="w-full sm:max-w-xl"
      >
        <SymbolPicker onAdded={() => setAdding(false)} />
      </Slideover>
    </div>
  );
}
