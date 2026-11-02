import { Link } from "@tanstack/react-router";
import { CircleAlert, CircleCheck, OctagonX, WifiOff } from "lucide-react";
import { Badge } from "lost-ui/ui/badge";
import { AlertsIndicator } from "@/components/shared/layout/alerts-indicator";
import { KillSwitchControl } from "@/components/shared/layout/kill-switch-control";
import { useOverview } from "@/hooks/shared/use-overview";
import { useConnections } from "@/hooks/shared/use-catalog";
import { useSystemStatus } from "@/hooks/shared/use-system";
import { isApiError } from "@/lib/shared/api/api-error";
import { BotState, ConnectionStatus } from "@/lib/shared/enums";
import { formatAge } from "@/lib/shared/dates";
import { AppEnv, env, environmentWarning } from "@/lib/shared/env";

const ICON = "size-4";
const HEADER_BADGE = "h-8 px-2.5 py-0";

export function SafetyStrip() {
  const status = useSystemStatus();
  const offline = status.isError && isApiError(status.error) && status.error.isNetwork;
  const data = status.data;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Link to="/system" className="flex flex-wrap items-center gap-1.5" title="Estado do sistema">
        <Badge
          variant={env.appEnv === AppEnv.Prod ? "default" : "outline"}
          className={HEADER_BADGE}
        >
          {env.appEnv}
        </Badge>
        {offline ? (
          <Badge variant="destructive" className={`${HEADER_BADGE} gap-1.5`}>
            <WifiOff className={ICON} aria-hidden="true" />
            API offline
          </Badge>
        ) : null}
        {data === undefined || offline ? null : (
          <Badge
            variant="outline"
            className={`${HEADER_BADGE} gap-1.5 ${data.worker.alive ? "border-success/40 text-success" : "border-destructive/40 text-destructive"}`}
          >
            {data.worker.alive ? (
              <CircleCheck className={ICON} aria-hidden="true" />
            ) : (
              <CircleAlert className={ICON} aria-hidden="true" />
            )}
            {data.worker.alive ? "Worker ativo" : "Worker parado"}
          </Badge>
        )}
        {data?.kill_switch.active ? (
          <Badge variant="destructive" className={`${HEADER_BADGE} gap-1.5`}>
            <OctagonX className={ICON} aria-hidden="true" />
            Kill switch ativo
          </Badge>
        ) : null}
      </Link>
      <div className="hidden sm:block">
        <AlertsIndicator />
      </div>
      <KillSwitchControl />
    </div>
  );
}

export function SystemBanners() {
  const status = useSystemStatus();
  const overview = useOverview();
  const connections = useConnections();
  const warning = environmentWarning(env.apiBaseUrl, env.appEnv);
  const data = status.data;
  const offline = status.isError && isApiError(status.error) && status.error.isNetwork;
  const failing = (overview.data ?? []).filter((bot) => bot.observed_state === BotState.Error);
  const stale = data?.stale_bots ?? [];
  const invalid = (connections.data ?? []).filter(
    (connection) => connection.status === ConnectionStatus.Invalid,
  );

  const notices = [
    ...(warning === null ? [] : [`Ambiente inconsistente: ${warning}`]),
    ...(offline ? ["API offline; os dados podem estar desatualizados."] : []),
    ...(data?.kill_switch.active
      ? [
          `Kill switch ativo: ${data.kill_switch.reason ?? "nenhum motivo informado"}. Novas ordens bloqueadas.`,
        ]
      : []),
    ...(data !== undefined && !data.worker.alive
      ? ["Worker parado; os bots não estão avançando e os números podem estar desatualizados."]
      : []),
    ...failing.map((bot) => `Bot ${bot.name} está em erro.`),
    ...stale.map(
      (bot) =>
        `Bot ${bot.name} sem heartbeat (${formatAge(bot.age_seconds === null ? null : Math.round(bot.age_seconds))}).`,
    ),
    ...invalid.map((connection) => `Conexão ${connection.label} está inválida.`),
  ];
  const critical =
    warning !== null ||
    offline ||
    data?.kill_switch.active === true ||
    failing.length > 0 ||
    stale.length > 0 ||
    invalid.length > 0;

  return (
    <>
      <div className="sm:hidden">
        <AlertsIndicator />
      </div>
      {notices.length === 0 ? null : (
        <div
          role="alert"
          aria-live={critical ? "assertive" : "polite"}
          className={`sticky top-0 z-40 flex flex-wrap items-start gap-3 rounded-md border px-4 py-3 shadow-md ${
            critical
              ? "border-destructive bg-destructive text-destructive-foreground"
              : "border-warning bg-warning text-warning-foreground"
          }`}
        >
          {critical ? (
            <OctagonX className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          ) : (
            <CircleAlert className="mt-0.5 size-5 shrink-0" aria-hidden="true" />
          )}
          <div className="min-w-0 flex-1 space-y-1">
            <p className="font-semibold">{critical ? "Atenção" : "Worker parado"}</p>
            <ul className="flex flex-wrap gap-x-2 gap-y-1 text-sm">
              {notices.map((notice) => (
                <li key={notice}>{notice}</li>
              ))}
            </ul>
          </div>
          <Link to="/system" className="shrink-0 text-sm font-medium underline underline-offset-4">
            Ver sistema
          </Link>
        </div>
      )}
    </>
  );
}
