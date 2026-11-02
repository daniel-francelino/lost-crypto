import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Brain, Database, Shield, Wallet } from "lucide-react";
import { PageHeader } from "lost-ui/app/page-header";
import { Form } from "lost-ui/forms/form";
import { FormInput } from "lost-ui/forms/form-input";
import { FormInputNumber } from "lost-ui/forms/form-input-number";
import { FormSelect } from "lost-ui/forms/form-select";
import { FormCheckbox } from "lost-ui/forms/form-checkbox";
import { FormSwitch } from "lost-ui/forms/form-switch";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle } from "@/components/shared/metrics/icon-card-title";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { SymbolSelect } from "@/components/shared/market-data/symbol-select";
import { CoverageNotice } from "@/components/shared/market-data/coverage-notice";
import { HalfLifeHint } from "@/components/backtests/half-life-hint";
import { DEFAULT_OFFSETS, START_OFFSET_KEY } from "@/lib/backtests/start-sensitivity";
import { BreaksWarning } from "@/components/shared/market-data/breaks-warning";
import { StrategyFields } from "@/components/shared/strategy/strategy-fields";
import { createBacktest, createSweep } from "@/lib/backtests/backtests.api";
import { BotLikeCard } from "@/components/backtests/bot-like-card";
import type { BacktestPrefill } from "@/lib/shared/backtest-prefill";
import {
  applyBacktestPrefill,
  type BacktestFormValues,
  CAPITAL_ITEMS,
  MAX_PARAMETERS,
  buildGrid,
  combinationCount,
  defaultBacktestValues,
  gridError,
  sampleAdvice,
  testFractionWarning,
  toBacktestInput,
} from "@/lib/backtests/form";
import { useRangeCoverage } from "@/hooks/shared/use-coverage";
import { formatInteger, numberText, numberValue } from "@/lib/shared/format";
import { gapsOverLimit } from "@/lib/shared/market-data/gaps";
import { useStrategies } from "@/hooks/shared/use-catalog";
import { useCapabilities } from "@/hooks/shared/use-system";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { decimalError, integerError } from "@/lib/shared/validators";
import { isDayString } from "@/lib/shared/dates";
import { SlippageModel, Timeframe } from "@/lib/shared/enums";
import { slippageModelLabel } from "@/lib/shared/labels";
import { defaultParamValues } from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const TIMEFRAMES = Object.values(Timeframe).map((value) => ({ label: value, value }));

type BacktestFormProps = {
  strategies: Strategy[];
  exchanges: string[];
  prefill: BacktestPrefill;
};

function BacktestForm({ strategies, exchanges, prefill }: BacktestFormProps) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const [values, setValues] = useState<BacktestFormValues>(() =>
    applyBacktestPrefill(defaultBacktestValues(strategies[0]), prefill, strategies),
  );
  const [error, setError] = useState<string | null>(null);
  const strategy = strategies.find((item) => item.type_key === values.strategyType);
  const set = <K extends keyof BacktestFormValues>(key: K, value: BacktestFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));

  const validRange = isDayString(values.start) && isDayString(values.end);
  const coverage = useRangeCoverage({
    exchange: values.exchange,
    symbol: values.symbol,
    timeframe: values.timeframe,
    start: values.start,
    end: values.end,
  });
  const range = validRange ? (coverage.data?.in_range ?? null) : null;
  const blockedByGaps = gapsOverLimit(range, values.timeframe) && !values.allowGaps;
  const advice = sampleAdvice(strategy, values.params, range?.expected ?? 0);
  const fractionWarning = testFractionWarning(values.testFraction);

  const grid = values.sweep ? buildGrid(strategy, values.grid) : {};
  const gridProblem = typeof grid === "string" ? grid : values.sweep ? gridError(grid) : undefined;

  const mutation = useMutation({
    mutationFn: async () => {
      const input = toBacktestInput(values, strategy);
      if (typeof grid !== "string" && values.sweep) {
        const sweep = await createSweep(input, grid);
        return { sweepId: sweep.id, runId: null };
      }
      const run = await createBacktest(input);
      return { sweepId: null, runId: run.id };
    },
    onSuccess: async (created) => {
      await client.invalidateQueries({ queryKey: QueryKey.Backtests.all() });
      if (created.sweepId !== null) {
        await navigate({ to: "/backtests/sweeps/$sweepId", params: { sweepId: created.sweepId } });
        return;
      }
      if (created.runId !== null) {
        await navigate({ to: "/backtests/$runId", params: { runId: created.runId } });
      }
    },
    onError: (failure) => setError(errorMessage(failure)),
  });

  return (
    <Form
      onSubmit={() => {
        setError(null);
        if (gridProblem !== undefined) {
          setError(gridProblem);
          return;
        }
        if (blockedByGaps) {
          setError(
            "Há lacunas acima do limite: importe os candles ou marque “Rodar mesmo com lacunas”.",
          );
          return;
        }
        mutation.mutate();
      }}
      className="space-y-6"
    >
      <Card>
        <CardHeader>
          <IconCardTitle className="text-base" icon={Database}>
            Dados
          </IconCardTitle>
          <CardDescription>
            Datas em UTC. O período precisa estar nos candles salvos.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <FormSelect
              label="Exchange"
              items={exchanges.map((value) => ({ label: value, value }))}
              value={values.exchange}
              onValueChange={(value) => set("exchange", value)}
            />
            <SymbolSelect
              label="Par"
              required
              value={values.symbol}
              onValueChange={(value) => set("symbol", value)}
            />
            <FormSelect
              label="Intervalo"
              items={TIMEFRAMES}
              value={values.timeframe}
              onValueChange={(value) => set("timeframe", value)}
            />
            <FormInput
              label="De (UTC)"
              type="date"
              value={values.start}
              onValueChange={(value) => set("start", value)}
              rules={[(value) => (isDayString(value ?? "") ? undefined : "Data inválida.")]}
            />
            <FormInput
              label="Até (UTC)"
              type="date"
              value={values.end}
              onValueChange={(value) => set("end", value)}
              rules={[
                (value) => (isDayString(value ?? "") ? undefined : "Data inválida."),
                () => (values.start <= values.end ? undefined : "O fim deve ser depois do início."),
              ]}
            />
          </div>
          {validRange ? (
            <CoverageNotice
              exchange={values.exchange}
              symbol={values.symbol}
              timeframe={values.timeframe}
              start={values.start}
              end={values.end}
            />
          ) : null}
          {gapsOverLimit(range, values.timeframe) ? (
            <FormCheckbox
              label="Rodar mesmo com lacunas"
              description="O motor executa os sinais na próxima abertura disponível; as lacunas ficam registradas no resultado."
              value={values.allowGaps}
              onValueChange={(value) => set("allowGaps", value)}
            />
          ) : null}
          {range === null || range.expected === 0 ? null : (
            <p className={advice.enough ? "text-sm text-muted-foreground" : "text-sm text-warning"}>
              Este período tem ~{formatInteger(range.expected)} candles. Com {advice.freeParameters}{" "}
              parâmetros livres, a regra prática do livro pede pelo menos{" "}
              {formatInteger(advice.minBars)} observações (252 por parâmetro)
              {advice.enough ? "." : ": amostra curta para tantos parâmetros."}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <IconCardTitle className="text-base" icon={Brain}>
            Estratégia
          </IconCardTitle>
          <CardDescription>{strategy?.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {strategy?.too_many_parameters === true ? (
            <p className="text-sm text-warning">
              Esta estratégia tem {strategy.parameter_count} parâmetros; o livro sugere no máximo{" "}
              {MAX_PARAMETERS} para não ajustar ao ruído.
            </p>
          ) : null}
          <FormSelect
            label="Estratégia"
            items={strategies.map((item) => ({ label: item.name, value: item.type_key }))}
            value={values.strategyType}
            onValueChange={(value) =>
              setValues((current) => ({
                ...current,
                strategyType: value,
                params: defaultParamValues(strategies.find((item) => item.type_key === value)),
                grid: {},
              }))
            }
          />
          <FormSwitch
            label="Varredura de parâmetros"
            description="Roda uma simulação para cada combinação de valores e compara os resultados."
            value={values.sweep}
            onValueChange={(value) => set("sweep", value)}
          />
          {values.sweep ? (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                Informe valores separados por vírgula (ex.: 5, 9, 12). Parâmetros em branco usam o
                valor padrão. Máximo de 200 combinações.
              </p>
              <div className="grid gap-4 sm:grid-cols-2">
                {strategy?.parameters.map((param) => (
                  <FormInput
                    key={param.name}
                    label={param.name}
                    description={param.description}
                    value={values.grid[param.name] ?? ""}
                    onValueChange={(value) => set("grid", { ...values.grid, [param.name]: value })}
                  />
                ))}
              </div>
              <div className="flex flex-wrap items-end gap-3">
                <FormInput
                  label="Sensibilidade à data inicial (dias de deslocamento)"
                  inputMode="numeric"
                  description="Roda a mesma configuração começando em dias diferentes (até 25 valores) e mostra a dispersão."
                  value={values.grid[START_OFFSET_KEY] ?? ""}
                  onValueChange={(value) =>
                    set("grid", { ...values.grid, [START_OFFSET_KEY]: value })
                  }
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={() =>
                    set("grid", { ...values.grid, [START_OFFSET_KEY]: DEFAULT_OFFSETS })
                  }
                >
                  Testar sensibilidade à data inicial
                </Button>
              </div>
              <p className="text-sm">
                {typeof grid === "string" ? grid : `${combinationCount(grid)} combinações.`}
              </p>
            </div>
          ) : (
            <StrategyFields
              strategy={strategy}
              values={values.params}
              onChange={(name, value) => set("params", { ...values.params, [name]: value })}
            />
          )}
          {validRange ? (
            <BreaksWarning
              exchange={values.exchange}
              symbol={values.symbol}
              start={values.start}
              end={values.end}
              onRestrict={(start, end) => setValues((current) => ({ ...current, start, end }))}
            />
          ) : null}
          {validRange ? (
            <HalfLifeHint
              exchange={values.exchange}
              symbol={values.symbol}
              timeframe={values.timeframe}
              start={values.start}
              end={values.end}
              strategyType={values.strategyType}
              onUseInSweep={(param, value) =>
                setValues((current) => ({
                  ...current,
                  sweep: true,
                  grid: { ...current.grid, [param]: value },
                }))
              }
            />
          ) : null}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <IconCardTitle className="text-base" icon={Wallet}>
            Capital, custos e validação
          </IconCardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          <FormSelect
            label="Capital inicial"
            required
            items={CAPITAL_ITEMS}
            value={values.initialCapital}
            onValueChange={(value) => set("initialCapital", value)}
          />
          <FormInputNumber
            label="Taxa (fração)"
            showControls={false}
            description="Vazio usa a taxa da exchange."
            value={numberValue(values.feeRate)}
            onValueChange={(value) => set("feeRate", numberText(value))}
            rules={[(value) => decimalError(numberText(value), false)]}
          />
          <FormInputNumber
            label="Slippage (bps)"
            required
            showControls={false}
            value={numberValue(values.slippageBps)}
            onValueChange={(value) => set("slippageBps", numberText(value))}
            rules={[(value) => decimalError(numberText(value), true)]}
          />
          <FormSelect
            label="Modelo de custo (slippage)"
            items={Object.values(SlippageModel).map((item) => ({
              label: slippageModelLabel(item),
              value: item,
            }))}
            value={values.slippageModel}
            onValueChange={(value) => set("slippageModel", value)}
          />
          {values.slippageModel === SlippageModel.Fixed ? null : (
            <>
              <FormInputNumber
                label="Slippage extra por volatilidade (k)"
                showControls={false}
                description="Bps extras por bps de amplitude do candle. Calibre com o slippage realizado dos seus bots; não há valor padrão."
                value={numberValue(values.slippageKRange)}
                onValueChange={(value) => set("slippageKRange", numberText(value))}
                rules={[(value) => decimalError(numberText(value), false)]}
              />
              <FormInputNumber
                label="Slippage extra por tamanho (k)"
                showControls={false}
                description="Bps extras por bps da fatia do valor negociado do candle que a ordem ocupa. O bot continua com custo fixo."
                value={numberValue(values.slippageKSize)}
                onValueChange={(value) => set("slippageKSize", numberText(value))}
                rules={[(value) => decimalError(numberText(value), false)]}
              />
            </>
          )}
          <FormInputNumber
            label="Semente"
            step={1}
            showControls={false}
            value={numberValue(values.seed)}
            onValueChange={(value) => set("seed", numberText(value))}
            rules={[(value) => integerError(numberText(value))]}
          />
          <FormInputNumber
            label="Fração fora da amostra"
            showControls={false}
            description="Parte final da série guardada para teste (0 a 1). Vazio desliga."
            value={numberValue(values.testFraction)}
            onValueChange={(value) => set("testFraction", numberText(value))}
            rules={[
              (value) => {
                const text = numberText(value).trim();
                if (text === "") return undefined;
                return (
                  decimalError(text, false) ??
                  (text.startsWith("0.") ? undefined : "Use um valor entre 0 e 1.")
                );
              },
              (value) => value === null || String(value).length <= 8 || "Limite: 8 caracteres.",
            ]}
          />
          {fractionWarning === undefined ? null : (
            <p className="text-sm text-warning sm:col-span-2 lg:col-span-5">{fractionWarning}</p>
          )}
        </CardContent>
      </Card>

      <BotLikeCard
        values={values}
        onChange={(next) => setValues((current) => ({ ...current, ...next }))}
      />

      <Card>
        <CardHeader>
          <IconCardTitle className="text-base" icon={Shield}>
            Robustez e tolerância
          </IconCardTitle>
          <CardDescription>
            Opcional. Mostra se o resultado aguenta custos maiores e se cabe no drawdown que você
            aceita.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {values.sweep ? (
            <p className="text-sm text-muted-foreground sm:col-span-2 lg:col-span-1">
              A sensibilidade a custos é por backtest: rode-a no resultado escolhido da varredura.
            </p>
          ) : (
            <FormSwitch
              label="Testar sensibilidade a custos"
              description="Repete a simulação com taxa e slippage de 0× a 3× e mostra onde o lucro some. Mais lento."
              value={values.costSensitivity}
              onValueChange={(value) => set("costSensitivity", value)}
            />
          )}
          <FormInput
            label="Drawdown máximo aceitável (%)"
            inputMode="decimal"
            description="Vazio desliga. O drawdown real costuma ser maior que o simulado."
            value={values.toleranceDrawdownPct}
            onValueChange={(value) => set("toleranceDrawdownPct", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Tempo máximo abaixo do pico (dias)"
            inputMode="numeric"
            description="Vazio desliga."
            value={values.toleranceDrawdownDays}
            onValueChange={(value) => set("toleranceDrawdownDays", value)}
            rules={[(value) => integerError(value ?? "")]}
          />
        </CardContent>
      </Card>

      {error === null ? null : (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="submit" disabled={mutation.isPending || blockedByGaps}>
          {mutation.isPending ? "Enviando…" : values.sweep ? "Rodar varredura" : "Rodar backtest"}
        </Button>
        <Button type="button" variant="outline" onClick={() => void navigate({ to: "/backtests" })}>
          Cancelar
        </Button>
      </div>
    </Form>
  );
}

export function BacktestFormPage({ prefill = {} }: { prefill?: BacktestPrefill }) {
  const strategies = useStrategies();
  const capabilities = useCapabilities();
  return (
    <div className="space-y-6">
      <PageHeader
        title="Novo backtest"
        description="Resultados são históricos e simulados; não garantem resultado futuro."
      />
      {strategies.isError ? (
        <ErrorBlock error={strategies.error} onRetry={() => void strategies.refetch()} />
      ) : strategies.data === undefined ? (
        <SkeletonBlock rows={5} />
      ) : (
        <BacktestForm
          strategies={strategies.data}
          exchanges={capabilities.data?.exchanges ?? ["binance"]}
          prefill={prefill}
        />
      )}
    </div>
  );
}
