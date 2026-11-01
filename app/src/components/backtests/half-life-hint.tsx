import { ChartNoAxesCombined } from "lucide-react";
import { Button } from "lost-ui/ui/button";
import { EmptyState } from "@/components/shared/feedback/empty-state";
import { SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { useHalfLife } from "@/hooks/shared/use-half-life";
import { gridValue, windowParamOf, windowsText } from "@/lib/backtests/half-life-hint";
import { formatRatio } from "@/lib/shared/format";

type Props = {
  exchange: string;
  symbol: string;
  timeframe: string;
  start: string;
  end: string;
  strategyType: string;
  onUseInSweep: (param: string, value: string) => void;
};

export function HalfLifeHint({
  exchange,
  symbol,
  timeframe,
  start,
  end,
  strategyType,
  onUseInSweep,
}: Props) {
  const query = useHalfLife({ exchange, symbol, timeframe, start, end });
  if (query.isPending) return query.fetchStatus === "idle" ? null : <SkeletonBlock rows={1} />;
  if (query.isError) return null;
  const estimate = query.data;
  const windows = estimate.suggested_windows;
  const text = windowsText(windows);
  const param = windowParamOf(strategyType);
  return (
    <div className="rounded-md border p-3 text-sm" aria-label="Dica de janela pela meia-vida">
      {text === null || windows === undefined ? (
        <EmptyState
          icon={<ChartNoAxesCombined aria-hidden="true" />}
          title="Sem meia-vida estimável"
          description="A série deste par e período não parece estacionária; não há janela sugerida."
          variant="naked"
          size="sm"
          className="items-start text-left p-0"
        />
      ) : (
        <div className="space-y-2">
          <p>
            Meia-vida ≈ {formatRatio(estimate.half_life_bars)} barras. Janelas em torno dela (0,5×,
            1×, 2×): <strong>{text}</strong>.
          </p>
          <p className="text-muted-foreground">
            Faixa de partida para uma busca, não recomendação. Só faz sentido para estratégias de
            reversão à média; confirme com treino × teste.
          </p>
          {param === null ? null : (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onUseInSweep(param, gridValue(windows))}
            >
              Usar na varredura ({param})
            </Button>
          )}
        </div>
      )}
    </div>
  );
}
