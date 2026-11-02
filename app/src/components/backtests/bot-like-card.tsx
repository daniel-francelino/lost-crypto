import { numberText, numberValue } from "@/lib/shared/format";
import { FormInputMoney } from "lost-ui/forms/form-input-money";
import { FormInputNumber } from "lost-ui/forms/form-input-number";
import { FormSelect } from "lost-ui/forms/form-select";
import { FormSwitch } from "lost-ui/forms/form-switch";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { BacktestFormValues, RiskValues } from "@/lib/backtests/form";
import { FillTiming, TradingProduct } from "@/lib/shared/enums";
import { decimalError, integerError } from "@/lib/shared/validators";

const TIMINGS = [
  { label: "Abertura do candle seguinte (padrão do backtest)", value: FillTiming.NextOpen },
  { label: "Fechamento do candle do sinal (como os bots)", value: FillTiming.SignalClose },
];

type Field = {
  key: keyof RiskValues;
  label: string;
  integer?: boolean;
  money?: boolean;
  hint?: string;
  futuresOnly?: boolean;
};

const quoteCurrency = (symbol: string): string | undefined => {
  const quote = symbol.split("/")[1]?.trim().toUpperCase();
  return quote !== undefined && /^[A-Z]{3}$/.test(quote) ? quote : undefined;
};

const FIELDS: Field[] = [
  { key: "maxPositionFraction", label: "Fração máxima por posição (0 a 1)" },
  { key: "maxOrderNotional", label: "Valor máximo por ordem", money: true },
  { key: "maxDailyLossPct", label: "Perda diária máxima (%)" },
  { key: "maxDrawdownPct", label: "Drawdown máximo (%)" },
  { key: "maxConsecutiveLosses", label: "Perdas consecutivas máximas", integer: true },
  { key: "maxRiskPerTradePct", label: "Risco máximo por operação (%)" },
  {
    key: "minLiquidationDistancePct",
    label: "Buffer mínimo até liquidação (%)",
    hint: "Recusa entradas se a liquidação estimada ficar mais perto que este percentual do preço de entrada.",
    futuresOnly: true,
  },
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
            {FIELDS.filter(
              (field) => !field.futuresOnly || values.product === TradingProduct.LinearPerpetual,
            ).map((field) => {
              const common = {
                label: field.label,
                description: field.hint ?? "Vazio desliga.",
                showControls: false,
                step: field.integer === true ? 1 : 0.1,
                min: 0,
                ...(field.key === "maxPositionFraction" ? { max: 1 } : {}),
                value: numberValue(String(values.risk[field.key])),
                onValueChange: (value: number | null) => setRisk(field.key, numberText(value)),
                rules: [
                  (value: number | null) =>
                    field.integer === true
                      ? integerError(numberText(value))
                      : decimalError(numberText(value), false),
                ],
              };
              if (field.money === true) {
                const currency = quoteCurrency(values.symbol);
                const { showControls: _showControls, step: _step, ...moneyProps } = common;
                return (
                  <FormInputMoney
                    key={field.key}
                    {...moneyProps}
                    {...(currency === undefined ? {} : { currency })}
                    locale="pt-PT"
                    fractionDigits={8}
                  />
                );
              }
              return <FormInputNumber key={field.key} {...common} />;
            })}
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
