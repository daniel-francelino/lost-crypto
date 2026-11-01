import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { SlippageModel } from "@/lib/shared/enums";
import { slippageModelLabel } from "@/lib/shared/labels";

export function CostModelNote({ run }: { run: Backtest }) {
  if (run.slippage_model === undefined || run.slippage_model === SlippageModel.Fixed) return null;
  return (
    <Alert className="border-warning/40">
      <AlertTitle>Modelo de custo: {slippageModelLabel(run.slippage_model)}</AlertTitle>
      <AlertDescription>
        O slippage desta execução cresce com a amplitude do candle e com o tamanho da ordem, e só
        piora o preenchimento. O bot usa custo fixo, então a paridade e a escada de custos (que só
        varia taxa e slippage base) não refletem este modelo.
      </AlertDescription>
    </Alert>
  );
}
