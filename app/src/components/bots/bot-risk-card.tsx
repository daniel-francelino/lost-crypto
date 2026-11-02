import { Shield } from "lucide-react";
import { FormInputMoney } from "lost-ui/forms/form-input-money";
import { FormInputNumber } from "lost-ui/forms/form-input-number";
import { FormSelect } from "lost-ui/forms/form-select";
import { FormSwitch } from "lost-ui/forms/form-switch";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle } from "@/components/shared/metrics/icon-card-title";
import type { BotFormValues } from "@/lib/bots/form";
import type { BotPrefill } from "@/lib/shared/bot-prefill";
import { DrawdownAction } from "@/lib/shared/enums";
import { drawdownActionLabel } from "@/lib/shared/labels";
import { decimalError, integerError } from "@/lib/shared/validators";
import { numberText, numberValue } from "@/lib/shared/format";

export function BotRiskCard({
  values,
  isFutures,
  prefill,
  set,
}: {
  values: BotFormValues;
  isFutures: boolean;
  prefill: BotPrefill;
  set: <K extends keyof BotFormValues>(key: K, value: BotFormValues[K]) => void;
}) {
  const quote = values.symbol.split("/")[1]?.split(":")[0]?.trim().toUpperCase();

  return (
    <Card>
      <CardHeader>
        <IconCardTitle className="text-base" icon={Shield}>
          Limites de risco
        </IconCardTitle>
        <CardDescription>
          Os limites do servidor valem sempre; no live os tetos globais valem ainda mais.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {isFutures ? (
          <FormInputNumber
            label="Distância mínima de liquidação (%)"
            showControls={false}
            description="Recusa entradas quando a liquidação estimada fica demasiado próxima."
            value={numberValue(values.minLiquidationDistancePct)}
            onValueChange={(value) => set("minLiquidationDistancePct", numberText(value))}
            rules={[(value) => decimalError(numberText(value), false)]}
          />
        ) : null}
        <FormInputNumber
          label="Fração máxima por posição"
          required
          showControls={false}
          step={0.01}
          min={0}
          max={1}
          description={
            prefill.maxPositionFraction === undefined
              ? "De 0 a 1 do capital."
              : "Pré-preenchida pela referência histórica do backtest; revise antes de criar."
          }
          value={numberValue(values.maxPositionFraction)}
          onValueChange={(value) => set("maxPositionFraction", numberText(value))}
          rules={[(value) => decimalError(numberText(value), true)]}
        />
        <FormInputMoney
          label="Valor máximo por ordem"
          {...(quote !== undefined && /^[A-Z]{3}$/.test(quote) ? { currency: quote } : {})}
          locale="pt-PT"
          fractionDigits={8}
          min={0}
          value={numberValue(values.maxOrderNotional)}
          onValueChange={(value) => set("maxOrderNotional", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormInputNumber
          label="Perda diária máxima (%)"
          showControls={false}
          value={numberValue(values.maxDailyLossPct)}
          onValueChange={(value) => set("maxDailyLossPct", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormInputNumber
          label="Drawdown máximo (%)"
          showControls={false}
          value={numberValue(values.maxDrawdownPct)}
          onValueChange={(value) => set("maxDrawdownPct", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormInputNumber
          label="Perdas consecutivas máximas"
          showControls={false}
          step={1}
          min={0}
          value={numberValue(values.maxConsecutiveLosses)}
          onValueChange={(value) => set("maxConsecutiveLosses", numberText(value))}
          rules={[(value) => integerError(numberText(value))]}
        />
        <FormInputNumber
          label="Risco máximo por operação (%)"
          showControls={false}
          value={numberValue(values.maxRiskPerTradePct)}
          onValueChange={(value) => set("maxRiskPerTradePct", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormInputNumber
          label="Amplitude máxima do candle (%)"
          showControls={false}
          value={numberValue(values.maxCandleRangePct)}
          onValueChange={(value) => set("maxCandleRangePct", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormInputNumber
          label="Máximo da ordem (% do volume médio)"
          showControls={false}
          description="Média do valor negociado nos últimos 20 candles. Vazio desliga. O livro sugere ~1% do volume diário (em ações)."
          value={numberValue(values.maxOrderPctOfVolume)}
          onValueChange={(value) => set("maxOrderPctOfVolume", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormSelect
          label="Ao atingir o drawdown máximo"
          items={Object.values(DrawdownAction).map((item) => ({
            label: drawdownActionLabel(item),
            value: item,
          }))}
          value={values.drawdownAction}
          onValueChange={(value) => set("drawdownAction", value)}
        />
        <FormInputNumber
          label="Salto máximo do fechamento (%)"
          showControls={false}
          description="Recusa entradas (nunca saídas) quando o fechamento se moveu mais que isso contra o fechamento anterior: um tick errado costuma aparecer como salto. Vazio desliga. Calibre com cuidado: quedas legítimas de cripto também são grandes."
          value={numberValue(values.maxCloseJumpPct)}
          onValueChange={(value) => set("maxCloseJumpPct", numberText(value))}
          rules={[(value) => decimalError(numberText(value), false)]}
        />
        <FormSwitch
          label="Exigir stop-loss"
          value={values.requireStopLoss}
          onValueChange={(value) => set("requireStopLoss", value)}
        />
      </CardContent>
    </Card>
  );
}
