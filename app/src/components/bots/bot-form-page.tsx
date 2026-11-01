import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader } from "lost-ui/app/page-header";
import { Form } from "lost-ui/forms/form";
import { FormInput } from "lost-ui/forms/form-input";
import { FormSelect } from "lost-ui/forms/form-select";
import { FormSwitch } from "lost-ui/forms/form-switch";
import { rules } from "lost-ui/forms/rules";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { StrategyFields } from "@/components/shared/strategy/strategy-fields";
import { useBot } from "@/hooks/bots/use-bots";
import { useConnections, useStrategies } from "@/hooks/shared/use-catalog";
import { useCapabilities } from "@/hooks/shared/use-system";
import { type Bot, createBot, updateBot } from "@/lib/bots/bots.api";
import { type BotFormValues, defaultFormValues, formFromBot, toBotInput } from "@/lib/bots/form";
import { ApiError } from "@/lib/shared/api/api-error";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { decimalError, integerError, symbolError } from "@/lib/shared/validators";
import { type BotPrefill, prefillParams } from "@/lib/shared/bot-prefill";
import { ConnectionStatus, Environment, ExecutionMode, Timeframe } from "@/lib/shared/enums";
import { defaultParamValues, paramsFromRecord } from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const MODE_ITEMS = [
  { label: "PAPER (simulado, sem exchange)", value: ExecutionMode.Paper },
  { label: "TESTNET (dinheiro fictício na exchange)", value: ExecutionMode.Testnet },
];
const TIMEFRAME_ITEMS = Object.values(Timeframe).map((value) => ({ label: value, value }));
const MAX_NAME = 60;

const prefilledValues = (strategies: Strategy[], prefill: BotPrefill): BotFormValues => {
  const strategy = strategies.find((item) => item.type_key === prefill.strategy) ?? strategies[0];
  const base = defaultFormValues(strategy);
  return {
    ...base,
    symbol: prefill.symbol ?? base.symbol,
    timeframe: prefill.timeframe ?? base.timeframe,
    params: paramsFromRecord(strategy, prefillParams(prefill)),
    maxDrawdownPct: prefill.maxDrawdownPct ?? base.maxDrawdownPct,
  };
};

type FormProps = {
  bot: Bot | null;
  strategies: Strategy[];
  exchanges: string[];
  prefill: BotPrefill;
};

function BotForm({ bot, strategies, exchanges, prefill }: FormProps) {
  const navigate = useNavigate();
  const client = useQueryClient();
  const connections = useConnections();
  const isLive = bot?.mode === ExecutionMode.Live;
  const [values, setValues] = useState<BotFormValues>(() =>
    bot === null
      ? prefilledValues(strategies, prefill)
      : formFromBot(
          bot,
          strategies.find((item) => item.type_key === bot.strategy_type),
        ),
  );
  const [serverErrors, setServerErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);

  const strategy = strategies.find((item) => item.type_key === values.strategyType);
  const set = <K extends keyof BotFormValues>(key: K, value: BotFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));
  const testnetConnections = (connections.data ?? []).filter(
    (item) => item.environment === Environment.Testnet && item.status === ConnectionStatus.Active,
  );

  const mutation = useMutation({
    mutationFn: () => {
      const input = toBotInput(values, strategy);
      if (bot === null) return createBot(input);
      if (!isLive) return updateBot(bot.id, input);
      const { mode: _mode, connection_id: _connection, ...rest } = input;
      return updateBot(bot.id, rest);
    },
    onSuccess: async (saved) => {
      await client.invalidateQueries({ queryKey: QueryKey.Bots.all() });
      toast.success(bot === null ? "Bot criado." : "Bot atualizado.");
      await navigate({ to: "/bots/$botId", params: { botId: saved.id }, search: {} });
    },
    onError: (error) => {
      setServerErrors(error instanceof ApiError ? error.fieldErrors : {});
      setFormError(errorMessage(error));
    },
  });

  const submit = () => {
    setServerErrors({});
    setFormError(null);
    mutation.mutate();
  };

  const err = (field: string) => serverErrors[field];

  return (
    <Form onSubmit={submit} className="space-y-6">
      {isLive ? (
        <Alert className="border-live/60">
          <AlertTitle>Bot LIVE</AlertTitle>
          <AlertDescription>
            Qualquer alteração invalida a aprovação atual: será preciso aprovar de novo antes de
            iniciar.
          </AlertDescription>
        </Alert>
      ) : null}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Identificação</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2">
          <FormInput
            label="Nome"
            required
            maxLength={MAX_NAME}
            value={values.name}
            onValueChange={(value) => set("name", value)}
            errorMessage={err("name") ?? ""}
            rules={[rules.required("Informe o nome.")]}
          />
          <FormSelect
            label="Exchange"
            items={exchanges.map((value) => ({ label: value, value }))}
            value={values.exchange}
            onValueChange={(value) => set("exchange", value)}
          />
          <FormInput
            label="Símbolo"
            required
            value={values.symbol}
            onValueChange={(value) => set("symbol", value)}
            errorMessage={err("symbol") ?? ""}
            rules={[(value) => symbolError(value ?? "")]}
          />
          <FormSelect
            label="Intervalo"
            items={TIMEFRAME_ITEMS}
            value={values.timeframe}
            onValueChange={(value) => set("timeframe", value)}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Estratégia</CardTitle>
          <CardDescription>{strategy?.description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <FormSelect
            label="Estratégia"
            items={strategies.map((item) => ({ label: item.name, value: item.type_key }))}
            value={values.strategyType}
            onValueChange={(value) => {
              const next = strategies.find((item) => item.type_key === value);
              setValues((current) => ({
                ...current,
                strategyType: value,
                params: defaultParamValues(next),
              }));
            }}
          />
          <StrategyFields
            strategy={strategy}
            values={values.params}
            onChange={(name, value) => set("params", { ...values.params, [name]: value })}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Capital e custos</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <FormInput
            label="Capital inicial"
            required
            inputMode="decimal"
            value={values.initialCapital}
            onValueChange={(value) => set("initialCapital", value)}
            errorMessage={err("initial_capital") ?? ""}
            rules={[(value) => decimalError(value ?? "", true)]}
          />
          <FormInput
            label="Taxa (fração)"
            inputMode="decimal"
            description="Vazio usa a taxa da exchange. Ex.: 0.001 = 0,1%."
            value={values.feeRate}
            onValueChange={(value) => set("feeRate", value)}
            errorMessage={err("fee_rate") ?? ""}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Slippage (bps)"
            required
            inputMode="decimal"
            value={values.slippageBps}
            onValueChange={(value) => set("slippageBps", value)}
            errorMessage={err("slippage_bps") ?? ""}
            rules={[(value) => decimalError(value ?? "", true)]}
          />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Limites de risco</CardTitle>
          <CardDescription>
            Os limites do servidor valem sempre; no live os tetos globais valem ainda mais.
          </CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <FormInput
            label="Fração máxima por posição"
            required
            inputMode="decimal"
            description="De 0 a 1 do capital."
            value={values.maxPositionFraction}
            onValueChange={(value) => set("maxPositionFraction", value)}
            rules={[(value) => decimalError(value ?? "", true)]}
          />
          <FormInput
            label="Valor máximo por ordem"
            inputMode="decimal"
            value={values.maxOrderNotional}
            onValueChange={(value) => set("maxOrderNotional", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Perda diária máxima (%)"
            inputMode="decimal"
            value={values.maxDailyLossPct}
            onValueChange={(value) => set("maxDailyLossPct", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Drawdown máximo (%)"
            inputMode="decimal"
            value={values.maxDrawdownPct}
            onValueChange={(value) => set("maxDrawdownPct", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Perdas consecutivas máximas"
            inputMode="numeric"
            value={values.maxConsecutiveLosses}
            onValueChange={(value) => set("maxConsecutiveLosses", value)}
            rules={[(value) => integerError(value ?? "")]}
          />
          <FormInput
            label="Risco máximo por operação (%)"
            inputMode="decimal"
            value={values.maxRiskPerTradePct}
            onValueChange={(value) => set("maxRiskPerTradePct", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Amplitude máxima do candle (%)"
            inputMode="decimal"
            value={values.maxCandleRangePct}
            onValueChange={(value) => set("maxCandleRangePct", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormInput
            label="Máximo da ordem (% do volume médio)"
            inputMode="decimal"
            description="Média do valor negociado nos últimos 20 candles. Vazio desliga. O livro sugere ~1% do volume diário (em ações)."
            value={values.maxOrderPctOfVolume}
            onValueChange={(value) => set("maxOrderPctOfVolume", value)}
            rules={[(value) => decimalError(value ?? "", false)]}
          />
          <FormSwitch
            label="Exigir stop-loss"
            value={values.requireStopLoss}
            onValueChange={(value) => set("requireStopLoss", value)}
          />
        </CardContent>
      </Card>

      {isLive ? null : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Modo de execução</CardTitle>
            <CardDescription>
              Bots LIVE não são criados aqui: use “Promover para LIVE” no detalhe de um bot parado.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-2">
            <FormSelect
              label="Modo"
              items={MODE_ITEMS}
              value={values.mode}
              onValueChange={(value) => set("mode", value)}
            />
            {values.mode === ExecutionMode.Paper ? null : (
              <FormSelect
                label="Conexão testnet ativa"
                placeholder={testnetConnections.length === 0 ? "Nenhuma conexão ativa" : "Escolha"}
                items={testnetConnections.map((item) => ({
                  label: `${item.label} (${item.api_key_hint})`,
                  value: item.id,
                }))}
                value={values.connectionId}
                onValueChange={(value) => set("connectionId", value)}
                rules={[rules.required("Escolha a conexão.")]}
              />
            )}
          </CardContent>
        </Card>
      )}

      {formError === null ? null : (
        <p role="alert" className="text-sm text-destructive">
          {formError}
        </p>
      )}
      <div className="flex gap-2">
        <Button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Salvando…" : bot === null ? "Criar bot" : "Salvar alterações"}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() =>
            void navigate({
              to: bot === null ? "/bots" : "/bots/$botId",
              params: bot === null ? {} : { botId: bot.id },
              search: {},
            })
          }
        >
          Cancelar
        </Button>
      </div>
    </Form>
  );
}

export function BotFormPage({
  botId,
  prefill = {},
}: {
  botId: string | null;
  prefill?: BotPrefill;
}) {
  const strategies = useStrategies();
  const capabilities = useCapabilities();
  const query = useBot(botId ?? "", botId !== null);
  const loadingBot = botId !== null && query.isPending;

  if (strategies.isError) {
    return <ErrorBlock error={strategies.error} onRetry={() => void strategies.refetch()} />;
  }
  if (botId !== null && query.isError) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  if (strategies.data === undefined || loadingBot) return <SkeletonBlock rows={6} />;

  return (
    <div className="space-y-6">
      <PageHeader
        title={botId === null ? "Novo bot" : `Editar ${query.data?.name ?? ""}`}
        description="Os limites de risco e a estratégia valem para cada operação do bot."
      />
      <BotForm
        key={query.data?.config_version ?? "new"}
        bot={botId === null ? null : (query.data ?? null)}
        strategies={strategies.data}
        exchanges={capabilities.data?.exchanges ?? ["binance"]}
        prefill={prefill}
      />
    </div>
  );
}
