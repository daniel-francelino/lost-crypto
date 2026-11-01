import { FormInput } from "lost-ui/forms/form-input";
import { FormSelect } from "lost-ui/forms/form-select";
import { FormSwitch } from "lost-ui/forms/form-switch";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { BacktestFormValues, RiskValues } from "@/lib/backtests/form";
import { FillTiming } from "@/lib/shared/enums";
import { decimalError, integerError } from "@/lib/shared/validators";

const TIMINGS = [
  { label: "Abertura do candle seguinte (padrão do backtest)", value: FillTiming.NextOpen },
  { label: "Fechamento do candle do sinal (como os bots)", value: FillTiming.SignalClose },
];

type Field = { key: keyof RiskValues; label: string; integer?: boolean; hint?: string };

const FIELDS: Field[] = [
  { key: "maxPositionFraction", label: "Fração máxima por posição (0 a 1)" },
  { key: "maxOrderNotional", label: "Valor máximo por ordem" },
  { key: "maxDailyLossPct", label: "Perda diária máxima (%)" },
  { key: "maxDrawdownPct", label: "Drawdown máximo (%)" },
  { key: "maxConsecutiveLosses", label: "Perdas consecutivas máximas", integer: true },
  { key: "maxRiskPerTradePct", label: "Risco máximo por operação (%)" },
  { key: "maxCandleRangePct", label: "Amplitude máxima do candle (%)" },
  {
    key: "maxOrderPctOfVolume",
    label: "Máximo da ordem (% do volume médio)",
    hint: "Média do valor negociado nos últimos 20 candles.",
  },
  {
    key: "maxCloseJumpPct",
    label: "Salto máximo do fechamento (%)",
    hint: "Recusa entradas depois de um salto contra o fechamento anterior. Vazio desliga.",
  },
];

type BotLikeCardProps = {
  values: BacktestFormValues;
  onChange: (next: Partial<BacktestFormValues>) => void;
};

export function BotLikeCard({ values, onChange }: BotLikeCardProps) {
  const setRisk = (key: keyof RiskValues, value: string | boolean) =>
    onChange({ risk: { ...values.risk, [key]: value } });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Execução e risco como no bot</CardTitle>
        <CardDescription>
          O backtest compra com todo o caixa e executa na abertura seguinte; os bots executam no
          fechamento do sinal e dimensionam pelos limites de risco, com pausas. Para comparar com um
          bot, use as mesmas regras.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <FormSelect
          label="Momento da execução"
          items={TIMINGS}
          value={values.fillTiming}
          onValueChange={(value) => onChange({ fillTiming: value })}
        />
        <FormSwitch
          label="Dimensionar como um bot"
          description="Passa cada sinal pelo módulo de risco do bot (tamanho, recusas) e pausa por perda diária, drawdown e perdas seguidas."
          value={values.riskEnabled}
          onValueChange={(value) => onChange({ riskEnabled: value })}
        />
        {values.riskEnabled ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FIELDS.map((field) => (
              <FormInput
                key={field.key}
                label={field.label}
                inputMode={field.integer === true ? "numeric" : "decimal"}
                description={field.hint ?? "Vazio desliga."}
                value={String(values.risk[field.key])}
                onValueChange={(value) => setRisk(field.key, value)}
                rules={[
                  (value) =>
                    field.integer === true
                      ? integerError(value ?? "")
                      : decimalError(value ?? "", false),
                ]}
              />
            ))}
            <FormSwitch
              label="Exigir stop-loss"
              value={values.risk.requireStopLoss}
              onValueChange={(value) => setRisk("requireStopLoss", value)}
            />
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
