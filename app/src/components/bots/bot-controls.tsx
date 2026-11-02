import { Pause, Pencil, Play, RotateCcw, Square, Trash2, Zap } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Button } from "lost-ui/ui/button";
import { toast } from "lost-ui/ui/sonner";
import { LiveFlow } from "@/components/bots/live-flow";
import { ConfirmDialog } from "@/components/shared/feedback/confirm-dialog";
import { BotCommand, isConverging, useBotCommand } from "@/hooks/bots/use-bots";
import { useSessionUser } from "@/hooks/shared/use-session";
import { useSystemStatus } from "@/hooks/shared/use-system";
import type { Bot } from "@/lib/bots/bots.api";
import { refusalMessage } from "@/lib/shared/api/messages";
import { Capability, can } from "@/lib/shared/capability";
import { BotState, ExecutionMode } from "@/lib/shared/enums";

const KILL_SWITCH_REASON = "Kill switch ativo.";
const SENT = "Comando enviado: aguardando o worker confirmar.";

const DialogKind = {
  Pause: "pause",
  Stop: "stop",
  Reset: "reset",
  Delete: "delete",
  Live: "live",
} as const;
type Dialog = (typeof DialogKind)[keyof typeof DialogKind] | null;

export function BotControls({ bot }: { bot: Bot }) {
  const user = useSessionUser();
  const status = useSystemStatus();
  const command = useBotCommand(bot.id);
  const navigate = useNavigate();
  const [dialog, setDialog] = useState<Dialog>(null);

  if (!can(user, Capability.BotsControl)) return null;

  const killSwitch = status.data?.kill_switch.active === true;
  const isLive = bot.mode === ExecutionMode.Live;
  const wantsRunning = bot.desired_state === BotState.Running;
  const settledStopped =
    bot.desired_state === BotState.Stopped && bot.observed_state !== BotState.Running;
  const busy = command.isPending || isConverging(bot.desired_state, bot.observed_state);

  const send = (name: BotCommand) =>
    command.mutate(
      { command: name },
      {
        onSuccess: () => toast(SENT),
        onError: (error) => toast.error(refusalMessage(error)),
      },
    );

  const start = () => {
    if (isLive) {
      setDialog(DialogKind.Live);
      return;
    }
    send(BotCommand.Start);
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Button
        onClick={start}
        disabled={wantsRunning || busy || killSwitch}
        title={killSwitch ? KILL_SWITCH_REASON : undefined}
        className="gap-1.5"
      >
        <Play className="size-4" aria-hidden="true" />
        {isLive ? "Iniciar (LIVE)…" : "Iniciar"}
      </Button>
      <Button
        variant="outline"
        onClick={() => setDialog(DialogKind.Pause)}
        disabled={!wantsRunning || busy}
        className="gap-1.5"
      >
        <Pause className="size-4" aria-hidden="true" />
        Pausar
      </Button>
      <Button
        variant="outline"
        onClick={() => setDialog(DialogKind.Stop)}
        disabled={bot.desired_state === BotState.Stopped || busy}
        className="gap-1.5"
      >
        <Square className="size-4" aria-hidden="true" />
        Parar
      </Button>
      {isLive ? null : (
        <Button
          variant="outline"
          onClick={() => setDialog(DialogKind.Reset)}
          disabled={!settledStopped || busy}
          title={settledStopped ? undefined : "Pare o bot antes de resetar o portfólio."}
          className="gap-1.5"
        >
          <RotateCcw className="size-4" aria-hidden="true" />
          Resetar portfólio
        </Button>
      )}
      {isLive ? null : (
        <Button
          variant="outline"
          onClick={() => setDialog(DialogKind.Delete)}
          disabled={!settledStopped || busy}
          title={settledStopped ? undefined : "Pare o bot antes de excluir."}
          className="gap-1.5 border-destructive/50 text-destructive"
        >
          <Trash2 className="size-4" aria-hidden="true" />
          Excluir
        </Button>
      )}
      {isLive || !can(user, Capability.BotsPromoteLive) ? null : (
        <Button
          variant="outline"
          onClick={() => setDialog(DialogKind.Live)}
          disabled={!settledStopped || busy}
          title={settledStopped ? undefined : "Pare o bot antes de promover."}
          className="gap-1.5 border-live/50 text-live"
        >
          <Zap className="size-4" aria-hidden="true" />
          Promover para LIVE…
        </Button>
      )}
      {can(user, Capability.BotsEdit) ? (
        <Button variant="ghost" asChild className="gap-1.5">
          <Link to="/bots/$botId/edit" params={{ botId: bot.id }}>
            <Pencil className="size-4" aria-hidden="true" />
            Editar
          </Link>
        </Button>
      ) : null}

      <ConfirmDialog
        open={dialog === DialogKind.Pause}
        onOpenChange={(open) => setDialog(open ? DialogKind.Pause : null)}
        title={`Pausar bot ${bot.name}?`}
        description="Interferir no plano pode piorar o resultado. Anote por que está pausando; não escreva senhas nem chaves."
        confirmLabel="Pausar bot"
        reasonLabel="Motivo (opcional)"
        reasonDescription="Não escreva senhas nem chaves."
        onConfirm={async (reason) => {
          await command.mutateAsync({ command: BotCommand.Pause, reason });
          toast(SENT);
        }}
      />
      <ConfirmDialog
        open={dialog === DialogKind.Stop}
        onOpenChange={(open) => setDialog(open ? DialogKind.Stop : null)}
        destructive
        title={`Parar bot ${bot.name}?`}
        description="O bot deixa de operar. Uma posição aberta é mantida; stops nativos continuam na exchange."
        confirmLabel="Parar bot"
        reasonLabel="Motivo (opcional)"
        reasonDescription="Não escreva senhas nem chaves."
        onConfirm={async (reason) => {
          await command.mutateAsync({ command: BotCommand.Stop, reason });
          toast(SENT);
        }}
      />
      <ConfirmDialog
        open={dialog === DialogKind.Reset}
        onOpenChange={(open) => setDialog(open ? DialogKind.Reset : null)}
        destructive
        title={`Resetar o portfólio de ${bot.name}?`}
        description="O portfólio virtual volta ao capital inicial. O histórico de ordens é mantido na auditoria."
        confirmLabel="Resetar portfólio"
        reasonLabel="Motivo (opcional)"
        reasonDescription="Não escreva senhas nem chaves."
        onConfirm={async (reason) => {
          await command.mutateAsync({ command: BotCommand.Reset, reason });
          toast.success("Portfólio resetado.");
        }}
      />
      <ConfirmDialog
        open={dialog === DialogKind.Delete}
        onOpenChange={(open) => setDialog(open ? DialogKind.Delete : null)}
        destructive
        title={`Excluir o bot ${bot.name}?`}
        description="O bot e todo o seu histórico (ordens, sinais, portfólio e curva de capital) são apagados e não podem ser recuperados. A auditoria guarda o registro da exclusão. Uma posição aberta precisa ser fechada antes."
        confirmLabel="Excluir bot"
        reasonLabel="Motivo (opcional)"
        reasonDescription="Não escreva senhas nem chaves."
        onConfirm={async (reason) => {
          await command.mutateAsync({ command: BotCommand.Delete, reason });
          toast.success("Bot excluído.");
          await navigate({ to: "/bots" });
        }}
      />
      <LiveFlow
        bot={bot}
        open={dialog === DialogKind.Live}
        onOpenChange={(open) => setDialog(open ? DialogKind.Live : null)}
      />
    </div>
  );
}
