import { Button } from "lost-ui/ui/button";
import { useRegimeBreaks } from "@/hooks/shared/use-regime-breaks";
import { isDayString } from "@/lib/shared/dates";
import { breaksCrossing, stretchesOf } from "@/lib/shared/market-data/regime-breaks";

type Props = {
  exchange: string;
  symbol: string;
  start: string;
  end: string;
  onRestrict?: (start: string, end: string) => void;
};

export function BreaksWarning({ exchange, symbol, start, end, onRestrict }: Props) {
  const valid = isDayString(start) && isDayString(end) && start < end && symbol.trim() !== "";
  const query = useRegimeBreaks({ exchange, symbol }, valid);
  if (!valid || query.data === undefined) return null;
  const crossing = breaksCrossing(query.data, exchange, symbol, start, end);
  if (crossing.length === 0) return null;
  const stretches = stretchesOf(crossing, start, end);
  return (
    <div className="space-y-2 rounded-md border border-warning p-3 text-sm" role="note">
      <p>
        Este período atravessa {crossing.length === 1 ? "a quebra" : "as quebras"}{" "}
        <strong>{crossing.map((item) => item.name).join(", ")}</strong>. Um ajuste ou uma meia-vida
        calculados através de uma quebra podem não valer. É só um aviso: nada é bloqueado.
      </p>
      {onRestrict === undefined ? null : (
        <div className="flex flex-wrap gap-2">
          {stretches.map((stretch) => (
            <Button
              key={stretch.start}
              type="button"
              variant="outline"
              size="sm"
              onClick={() => onRestrict(stretch.start, stretch.end)}
            >
              Limitar a este regime: {stretch.label} ({stretch.start} a {stretch.end})
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}
