import { useMutation, useQueryClient } from "@tanstack/react-query";
import { CircleAlert, CircleCheck, Zap } from "lucide-react";
import { useState } from "react";
import { Modal } from "lost-ui/elements/modal";
import { Stepper } from "lost-ui/elements/stepper";
import { Form } from "lost-ui/forms/form";
import { FormInput } from "lost-ui/forms/form-input";
import { FormSelect } from "lost-ui/forms/form-select";
import { rules } from "lost-ui/forms/rules";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { toast } from "lost-ui/ui/sonner";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { useNow } from "@/hooks/shared/use-now";
import { useReadiness } from "@/hooks/bots/use-bots";
import { useConnections } from "@/hooks/shared/use-catalog";
import { useCapabilities } from "@/hooks/shared/use-system";
import {
  type Approval,
  type Bot,
  promoteToLive,
  requestApproval,
  startBot,
} from "@/lib/bots/bots.api";
import { refusalMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { countdownSeconds } from "@/lib/shared/dates";
import { ConnectionStatus, Environment, ExecutionMode } from "@/lib/shared/enums";

const Step = {
  Readiness: "readiness",
  Promote: "promote",
  Approve: "approve",
  Start: "start",
} as const;
type Step = (typeof Step)[keyof typeof Step];

type LiveFlowProps = { bot: Bot; open: boolean; onOpenChange: (open: boolean) => void };

const secondsText = (seconds: number): string =>
  `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;

export function LiveFlow({ bot, open, onOpenChange }: LiveFlowProps) {
  const client = useQueryClient();
  const isLive = bot.mode === ExecutionMode.Live;
  const [step, setStep] = useState<Step>(Step.Readiness);
  const [connectionId, setConnectionId] = useState("");
  const [typedName, setTypedName] = useState("");
  const [approval, setApproval] = useState<Approval | null>(null);
  const [refusal, setRefusal] = useState<string | null>(null);

  const capabilities = useCapabilities();
  const readiness = useReadiness(bot.id, open);
  const connections = useConnections();
  const now = useNow();

  const remaining = approval === null ? 0 : countdownSeconds(approval.expires_at, now);
  const expired = approval !== null && remaining === 0;
  const activeLive = (connections.data ?? []).filter(
    (item) => item.environment === Environment.Live && item.status === ConnectionStatus.Active,
  );

  const refresh = () => client.invalidateQueries({ queryKey: QueryKey.Bots.all() });

  const promote = useMutation({
    mutationFn: () => promoteToLive(bot.id, connectionId),
    onSuccess: async () => {
      await refresh();
      setStep(Step.Approve);
    },
    onError: (error) => setRefusal(refusalMessage(error)),
  });

  const approve = useMutation({
    mutationFn: () => requestApproval(bot.id, typedName),
    onSuccess: (result) => {
      setApproval(result);
      setStep(Step.Start);
    },
    onError: (error) => setRefusal(refusalMessage(error)),
  });

  const start = useMutation({
    mutationFn: () => startBot(bot.id, approval?.confirmation_token ?? null),
    onSuccess: async () => {
      await refresh();
      toast("Início enviado: aguardando o worker confirmar.");
      setApproval(null);
      setTypedName("");
      onOpenChange(false);
    },
    onError: (error) => setRefusal(refusalMessage(error)),
  });

  const blockers =
    capabilities.data?.live_available === false ? capabilities.data.live_blockers : [];
  const current = expired && step === Step.Start ? Step.Approve : step;
  const stepIndex = [Step.Readiness, Step.Promote, Step.Approve, Step.Start].indexOf(current);

  const close = (next: boolean) => {
    if (!next) {
      setApproval(null);
      setTypedName("");
      setRefusal(null);
      setStep(Step.Readiness);
    }
    onOpenChange(next);
  };

  return (
    <Modal
      open={open}
      onOpenChange={close}
      title={isLive ? "Iniciar bot LIVE" : "Promover para LIVE"}
      description="Dinheiro real. Cada etapa precisa ser confirmada; o servidor recusa o que estiver faltando."
    >
      <div className="space-y-4">
        <Stepper
          size="sm"
          value={stepIndex}
          linear
          items={[
            { title: "Prontidão" },
            { title: "Promoção", disabled: isLive },
            { title: "Aprovação" },
            { title: "Início" },
          ]}
        />
        {blockers.length === 0 ? null : (
          <Alert variant="destructive">
            <CircleAlert className="size-4" aria-hidden="true" />
            <AlertTitle>O live não está disponível neste ambiente</AlertTitle>
            <AlertDescription>
              <ul className="list-disc pl-4">
                {blockers.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </AlertDescription>
          </Alert>
        )}

        {current === Step.Readiness ? (
          <section className="space-y-3" aria-label="Prontidão">
            {readiness.isPending ? <SkeletonBlock rows={3} /> : null}
            {readiness.isError ? (
              <ErrorBlock error={readiness.error} onRetry={() => void readiness.refetch()} />
            ) : null}
            {readiness.data === undefined ? null : (
              <ul className="space-y-2">
                {readiness.data.checks.map((check) => (
                  <li key={check.name} className="flex items-start gap-2 text-sm">
                    {check.ok ? (
                      <CircleCheck className="mt-0.5 size-4 text-success" aria-label="ok" />
                    ) : (
                      <CircleAlert
                        className="mt-0.5 size-4 text-destructive"
                        aria-label="pendente"
                      />
                    )}
                    <span>
                      <strong>{check.name}</strong>
                      <span className="block text-muted-foreground">{check.detail}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => void readiness.refetch()}>
                Verificar de novo
              </Button>
              <Button
                disabled={readiness.data?.ready !== true || blockers.length > 0}
                onClick={() => setStep(isLive ? Step.Approve : Step.Promote)}
              >
                Continuar
              </Button>
            </div>
          </section>
        ) : null}

        {current === Step.Promote ? (
          <section className="space-y-3" aria-label="Promoção">
            <FormSelect
              label="Conexão live ativa"
              placeholder={activeLive.length === 0 ? "Nenhuma conexão live ativa" : "Escolha"}
              items={activeLive.map((item) => ({
                label: `${item.label} (${item.api_key_hint})`,
                value: item.id,
              }))}
              value={connectionId}
              onValueChange={setConnectionId}
            />
            <p className="text-sm text-muted-foreground">
              O bot precisa estar parado, sem posição aberta e com histórico limpo de paper.
            </p>
            <div className="flex justify-end">
              <Button
                disabled={connectionId === "" || promote.isPending}
                onClick={() => {
                  setRefusal(null);
                  promote.mutate();
                }}
              >
                {promote.isPending ? "Promovendo…" : "Promover para LIVE"}
              </Button>
            </div>
          </section>
        ) : null}

        {current === Step.Approve ? (
          <section className="space-y-3" aria-label="Aprovação">
            <Form
              onSubmit={() => {
                setRefusal(null);
                approve.mutate();
              }}
              className="space-y-3"
            >
              <FormInput
                label={`Digite o nome do bot (${bot.name}) para aprovar`}
                value={typedName}
                onValueChange={setTypedName}
                autoComplete="off"
                rules={[rules.matches(() => bot.name, "O nome digitado não confere.")]}
              />
              <p className="text-sm text-muted-foreground">
                A aprovação vale por poucos minutos, uma única vez, e deve ser refeita a cada
                início.
              </p>
              <div className="flex justify-end">
                <Button type="submit" disabled={approve.isPending}>
                  {approve.isPending ? "Aprovando…" : "Pedir aprovação"}
                </Button>
              </div>
            </Form>
          </section>
        ) : null}

        {current === Step.Start && approval !== null ? (
          <section className="space-y-3" aria-label="Início">
            <Alert className="border-live/50">
              <Zap className="size-4 text-live" aria-hidden="true" />
              <AlertTitle>Aprovado. Expira em {secondsText(remaining)}</AlertTitle>
              <AlertDescription>
                Ao iniciar, o bot passa a enviar ordens reais dentro dos tetos configurados.
              </AlertDescription>
            </Alert>
            <div className="flex justify-end">
              <Button
                className="bg-live text-live-foreground hover:bg-live/90"
                disabled={start.isPending}
                onClick={() => {
                  setRefusal(null);
                  start.mutate();
                }}
              >
                {start.isPending ? "Iniciando…" : "Iniciar bot LIVE"}
              </Button>
            </div>
          </section>
        ) : null}

        {expired ? (
          <p role="alert" className="text-sm text-warning">
            A aprovação expirou. Peça uma nova.
          </p>
        ) : null}
        {refusal === null ? null : (
          <p role="alert" className="text-sm text-destructive">
            {refusal}
          </p>
        )}
      </div>
    </Modal>
  );
}
