import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Bot as BotIcon, Brain, Diff, Radio, Shield, Wallet } from "lucide-react";
import { PageHeader } from "lost-ui/app/page-header";
import { Form } from "lost-ui/forms/form";
import { FormInput } from "lost-ui/forms/form-input";
import { FormInputMoney } from "lost-ui/forms/form-input-money";
import { FormInputNumber } from "lost-ui/forms/form-input-number";
import { FormSelect } from "lost-ui/forms/form-select";
import { FormSwitch } from "lost-ui/forms/form-switch";
import { rules } from "lost-ui/forms/rules";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { ConfirmDialog } from "@/components/shared/feedback/confirm-dialog";
import { EmptyState } from "@/components/shared/feedback/empty-state";
import { backtestPrefillFromBot } from "@/lib/bots/execution";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { IconCardTitle } from "@/components/shared/metrics/icon-card-title";
import { StrategyFields } from "@/components/shared/strategy/strategy-fields";
import { useBot, useOrders, useOverview, usePerformance } from "@/hooks/bots/use-bots";
import { useConnections, useStrategies } from "@/hooks/shared/use-catalog";
import { useCapabilities } from "@/hooks/shared/use-system";
import { type Bot, createBot, updateBot } from "@/lib/bots/bots.api";
import { type BotFormValues, defaultFormValues, formFromBot, toBotInput } from "@/lib/bots/form";
import { ApiError } from "@/lib/shared/api/api-error";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { decimalError, integerError } from "@/lib/shared/validators";
import { SymbolSelect } from "@/components/shared/market-data/symbol-select";
import { type BotPrefill, prefillParams } from "@/lib/shared/bot-prefill";
import {
  ConnectionStatus,
  DrawdownAction,
  Environment,
  ExecutionMode,
  Timeframe,
} from "@/lib/shared/enums";
import { drawdownActionLabel } from "@/lib/shared/labels";
import { AppRoute } from "@/lib/shared/routes";
import { defaultParamValues, paramsFromRecord } from "@/lib/shared/strategies/params";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

const MODE_ITEMS = [
  { label: "PAPER (simulado, sem exchange)", value: ExecutionMode.Paper },
  { label: "TESTNET (dinheiro fictício na exchange)", value: ExecutionMode.Testnet },
];
const TIMEFRAME_ITEMS = Object.values(Timeframe).map((value) => ({ label: value, value }));
const MAX_NAME = 60;
const numberValue = (value: string): number | null => (value.trim() === "" ? null : Number(value));
const numberText = (value: number | null): string => (value === null ? "" : String(value));
const quoteCurrency = (symbol: string): string | undefined => {
  const quote = symbol.split("/")[1]?.trim().toUpperCase();
  return quote !== undefined && /^[A-Z]{3}$/.test(quote) ? quote : undefined;
};
const quoteCurrencyProps = (symbol: string): { currency?: string } => {
  const currency = quoteCurrency(symbol);
  return currency === undefined ? {} : { currency };
};
const CHANGE_LABELS: Record<string, string> = {
  name: "Nome",
  exchange: "Exchange",
  strategy_type: "Estratégia",
  strategy_params: "Parâmetros",
  symbol: "Símbolo",
  timeframe: "Intervalo",
  initial_capital: "Capital inicial",
  fee_rate: "Taxa",
  slippage_bps: "Slippage",
  risk: "Limites de risco",
  mode: "Modo",
  connection_id: "Conexão",
};

const prefilledValues = (strategies: Strategy[], prefill: BotPrefill): BotFormValues => {
  const strategy = strategies.find((item) => item.type_key === prefill.strategy) ?? strategies[0];
  const base = defaultFormValues(strategy);
  return {
    ...base,
    symbol: prefill.symbol ?? base.symbol,
    timeframe: prefill.timeframe ?? base.timeframe,
    params: paramsFromRecord(strategy, prefillParams(prefill)),
    maxDrawdownPct: prefill.maxDrawdownPct ?? base.maxDrawdownPct,
    maxPositionFraction: prefill.maxPositionFraction ?? base.maxPositionFraction,
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
  const [confirmEdit, setConfirmEdit] = useState(false);
  const orderHistory = useOrders(bot?.id ?? "", 1, 0, bot !== null);
  const overview = useOverview();
  const performance = usePerformance(bot?.id ?? "", bot !== null);

  const strategy = strategies.find((item) => item.type_key === values.strategyType);
  const originalStrategy = strategies.find((item) => item.type_key === bot?.strategy_type);
  const currentInput = bot === null ? null : toBotInput(values, strategy);
  const originalInput =
    bot === null ? null : toBotInput(formFromBot(bot, originalStrategy), originalStrategy);
  const pendingChanges =
    currentInput === null || originalInput === null
      ? []
      : Object.entries(currentInput)
          .filter(
            ([key, value]) =>
              JSON.stringify(value) !==
              JSON.stringify(originalInput[key as keyof typeof originalInput]),
          )
          .map(([key, after]) => ({
            key,
            before: originalInput[key as keyof typeof originalInput],
            after,
          }));
  const set = <K extends keyof BotFormValues>(key: K, value: BotFormValues[K]) =>
    setValues((current) => ({ ...current, [key]: value }));
  const testnetConnections = (connections.data ?? []).filter(
    (item) => item.environment === Environment.Testnet && item.status === ConnectionStatus.Active,
  );

  const mutation = useMutation({
    mutationFn: (reason?: string) => {
      const input = toBotInput(values, strategy);
      if (bot === null) return createBot(input);
      if (!isLive)
        return updateBot(bot.id, {
          ...input,
          ...(reason === undefined ? {} : { change_reason: reason }),
        });
      const { mode: _mode, connection_id: _connection, ...rest } = input;
      return updateBot(bot.id, {
        ...rest,
        ...(reason === undefined ? {} : { change_reason: reason }),
      });
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
    if (bot === null) mutation.mutate(undefined);
    else setConfirmEdit(true);
  };

  const err = (field: string) => serverErrors[field];

  return (
    <>
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
            <IconCardTitle className="text-base" icon={BotIcon}>
              Identificação
            </IconCardTitle>
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
            <SymbolSelect
              label="Par"
              required
              value={values.symbol}
              onValueChange={(value) => set("symbol", value)}
              errorMessage={err("symbol") ?? ""}
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
            <IconCardTitle className="text-base" icon={Brain}>
              Estratégia
            </IconCardTitle>
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
            <IconCardTitle className="text-base" icon={Wallet}>
              Capital e custos
            </IconCardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3">
            <FormInputMoney
              label="Capital inicial"
              required
              {...quoteCurrencyProps(values.symbol)}
              locale="pt-PT"
              fractionDigits={8}
              min={0}
              value={numberValue(values.initialCapital)}
              onValueChange={(value) => set("initialCapital", numberText(value))}
              errorMessage={err("initial_capital") ?? ""}
              rules={[(value) => decimalError(numberText(value), true)]}
            />
            <FormInputNumber
              label="Taxa (fração)"
              showControls={false}
              description="Vazio usa a taxa da exchange. Ex.: 0.001 = 0,1%."
              value={numberValue(values.feeRate)}
              onValueChange={(value) => set("feeRate", numberText(value))}
              errorMessage={err("fee_rate") ?? ""}
              rules={[(value) => decimalError(numberText(value), false)]}
            />
            <FormInputNumber
              label="Slippage (bps)"
              required
              showControls={false}
              value={numberValue(values.slippageBps)}
              onValueChange={(value) => set("slippageBps", numberText(value))}
              errorMessage={err("slippage_bps") ?? ""}
              rules={[(value) => decimalError(numberText(value), true)]}
            />
          </CardContent>
        </Card>

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
              {...quoteCurrencyProps(values.symbol)}
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

        {isLive ? null : (
          <Card>
            <CardHeader>
              <IconCardTitle className="text-base" icon={Radio}>
                Modo de execução
              </IconCardTitle>
              <CardDescription>
                Bots LIVE não são criados aqui: use “Promover para LIVE” no detalhe de um bot
                parado.
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
                  placeholder={
                    testnetConnections.length === 0 ? "Nenhuma conexão ativa" : "Escolha"
                  }
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
      {bot === null ? null : (
        <ConfirmDialog
          open={confirmEdit}
          onOpenChange={setConfirmEdit}
          title="Confirmar alterações"
          description={
            <div className="space-y-3">
              <p>
                Alterar parâmetros depois de perdas pode ser uma armadilha de representatividade.
                Teste a mudança em um período longo antes de operar.
              </p>
              <p>
                Retorno atual:{" "}
                {overview.data?.find((item) => item.id === bot.id)?.return_pct ?? "sem dados"}% |
                drawdown atual: {performance.data?.current_drawdown_pct ?? "sem dados"}%
              </p>
              {isLive ? (
                <p>
                  A aprovação LIVE atual será invalidada; será necessária uma nova aprovação para
                  iniciar.
                </p>
              ) : null}
              {currentInput === null ? null : (
                <Link
                  to={AppRoute.BacktestsNew}
                  search={backtestPrefillFromBot({
                    ...bot,
                    strategy_type: currentInput.strategy_type,
                    strategy_params: currentInput.strategy_params,
                    symbol: currentInput.symbol,
                    timeframe: currentInput.timeframe,
                    fee_rate: currentInput.fee_rate ?? bot.fee_rate,
                    slippage_bps: currentInput.slippage_bps,
                    risk: currentInput.risk,
                  })}
                  className="inline-block underline-offset-4 hover:underline"
                >
                  Rodar backtest com esta configuração
                </Link>
              )}
              {pendingChanges.length === 0 ? (
                <EmptyState
                  icon={<Diff aria-hidden="true" />}
                  title="Nenhuma diferença detectada"
                  variant="naked"
                  size="sm"
                />
              ) : (
                <ul className="max-h-48 space-y-1 overflow-y-auto rounded border p-3 text-sm">
                  {pendingChanges.map(({ key, before, after }) => (
                    <li key={key}>
                      <strong>{CHANGE_LABELS[key] ?? key}:</strong> {JSON.stringify(before)} →{" "}
                      {JSON.stringify(after)}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          }
          confirmLabel="Salvar alterações"
          reasonLabel="Motivo da alteração"
          reasonDescription="Não escreva senhas nem chaves."
          reasonRequired={(orderHistory.data?.total ?? 1) > 0}
          onConfirm={async (reason) => {
            await mutation.mutateAsync(reason);
          }}
        />
      )}
    </>
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
