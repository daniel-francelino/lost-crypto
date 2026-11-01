import { Link } from "@tanstack/react-router";
import { Copy } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { toast } from "lost-ui/ui/sonner";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import { formatDateTime } from "@/lib/shared/dates";
import { env } from "@/lib/shared/env";
import { formatInteger, formatPrice, formatQuantity } from "@/lib/shared/format";
import { type SystemStatus, WORKER_HEALTH_PATH } from "@/lib/shared/system/system.api";

const WARN = "text-warning";

const backupHint = (status: SystemStatus): string => {
  const backup = status.backup;
  if (backup === null || backup === undefined || backup.last_backup === null) {
    return "Nenhum backup registrado: rode `make backup`.";
  }
  const restore = backup.last_restore_check;
  const restoreText =
    restore === null
      ? "restauração nunca testada"
      : `restauração ${restore.ok ? "testada" : "FALHOU"} em ${formatDateTime(restore.at)}`;
  return `Último: ${formatDateTime(backup.last_backup.at)}${backup.last_backup.ok ? "" : " (falhou)"} · ${restoreText}`;
};

const clockText = (status: SystemStatus): { value: string; hint: string; warn: boolean } => {
  const clock = status.clock;
  if (clock === null || clock === undefined || clock.skew_ms === null) {
    return { value: "—", hint: "Ainda não medido pelo worker.", warn: false };
  }
  const hint = clock.blocking_live
    ? "Acima de 5 s: novas posições live bloqueadas. Ative a sincronização (NTP)."
    : clock.warning
      ? "Acima de 1 s: ative a sincronização de horário (NTP)."
      : `Medido em ${formatDateTime(clock.measured_at)}.`;
  return { value: `${formatInteger(clock.skew_ms)} ms`, hint, warn: clock.warning };
};

export function OperationsTiles({ status }: { status: SystemStatus }) {
  const exposed = status.unprotected_positions?.length ?? 0;
  const clock = clockText(status);
  const backupWarn = status.backup?.overdue ?? true;
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      <StatTile
        label="Posições sem stop na exchange"
        value={<span className={exposed > 0 ? WARN : undefined}>{exposed}</span>}
        hint={
          exposed > 0
            ? "Expostas se o worker cair: só um stop na exchange protege numa queda."
            : "Toda posição testnet/live tem stop na exchange."
        }
      />
      <StatTile
        label="Relógio × exchange"
        value={<span className={clock.warn ? WARN : undefined}>{clock.value}</span>}
        hint={clock.hint}
      />
      <StatTile
        label="Backup"
        value={
          <span className={backupWarn ? WARN : undefined}>
            {backupWarn ? "Atrasado" : "Em dia"}
          </span>
        }
        hint={backupHint(status)}
      />
    </div>
  );
}

export function UnprotectedPositions({ status }: { status: SystemStatus }) {
  const positions = status.unprotected_positions ?? [];
  if (positions.length === 0) return null;
  return (
    <Alert className="border-warning/50">
      <AlertTitle>Posições expostas numa queda do worker</AlertTitle>
      <AlertDescription>
        <p className="mb-2">
          Estas posições não têm stop guardado na exchange. Se o servidor cair, nada as protege até
          ele voltar.
        </p>
        <ul className="space-y-1">
          {positions.map((position) => (
            <li key={position.bot_id}>
              <Link
                to="/bots/$botId"
                params={{ botId: position.bot_id }}
                className="font-medium underline-offset-4 hover:underline"
              >
                {position.name}
              </Link>{" "}
              — {position.symbol} ({position.mode}), {formatQuantity(position.quantity)}
              {position.stop_price === null
                ? ", sem stop"
                : `, stop vigiado só pelo worker em ${formatPrice(position.stop_price)}`}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  );
}

export function ExternalMonitorCard({ alive }: { alive: boolean }) {
  const url = `${env.apiBaseUrl}${WORKER_HEALTH_PATH}`;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Monitoramento externo</CardTitle>
        <CardDescription>
          Esta tela só avisa quem está com o app aberto. Para saber de uma queda do servidor
          inteiro, aponte um monitor de fora (UptimeRobot, Healthchecks.io, um cron em outra
          máquina) para este endereço: ele responde 503 quando o worker para.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap items-center gap-2">
        <code className="break-all rounded bg-muted px-2 py-1 text-xs">{url}</code>
        <Button
          size="sm"
          variant="outline"
          className="gap-1.5"
          onClick={() =>
            void navigator.clipboard
              .writeText(url)
              .then(() => toast("Endereço copiado."))
              .catch(() => toast("Não foi possível copiar; selecione o texto."))
          }
        >
          <Copy className="size-3.5" aria-hidden="true" />
          Copiar
        </Button>
        <span className="text-sm text-muted-foreground">
          Agora: {alive ? "worker ativo (200)" : "worker parado (503)"}
        </span>
      </CardContent>
    </Card>
  );
}
