import { Link } from "@tanstack/react-router";
import { CircleAlert, CircleCheck, OctagonX, WifiOff } from "lucide-react";
import { Badge } from "lost-ui/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { AlertsIndicator } from "@/components/shared/layout/alerts-indicator";
import { KillSwitchControl } from "@/components/shared/layout/kill-switch-control";
import { useSystemStatus } from "@/hooks/shared/use-system";
import { isApiError } from "@/lib/shared/api/api-error";
import { AppEnv, env, environmentWarning } from "@/lib/shared/env";

const ICON = "size-3";

export function SafetyStrip() {
  const status = useSystemStatus();
  const offline = status.isError && isApiError(status.error) && status.error.isNetwork;
  const data = status.data;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <Link to="/system" className="flex flex-wrap items-center gap-1.5" title="Estado do sistema">
        <Badge variant={env.appEnv === AppEnv.Prod ? "default" : "outline"}>{env.appEnv}</Badge>
        {offline ? (
          <Badge variant="destructive" className="gap-1">
            <WifiOff className={ICON} aria-hidden="true" />
            API offline
          </Badge>
        ) : null}
        {data === undefined || offline ? null : (
          <Badge
            variant="outline"
            className={`gap-1 ${data.worker.alive ? "border-success/40 text-success" : "border-destructive/40 text-destructive"}`}
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
          <Badge variant="destructive" className="gap-1">
            <OctagonX className={ICON} aria-hidden="true" />
            Kill switch ativo
          </Badge>
        ) : null}
      </Link>
      <AlertsIndicator />
      <KillSwitchControl />
    </div>
  );
}

export function SystemBanners() {
  const status = useSystemStatus();
  const warning = environmentWarning(env.apiBaseUrl, env.appEnv);
  const data = status.data;

  return (
    <div className="space-y-3 empty:hidden">
      {warning === null ? null : (
        <Alert variant="destructive">
          <AlertTitle>Ambiente inconsistente</AlertTitle>
          <AlertDescription>{warning}</AlertDescription>
        </Alert>
      )}
      {data?.kill_switch.active ? (
        <Alert variant="destructive">
          <OctagonX className="size-4" aria-hidden="true" />
          <AlertTitle>Kill switch ativo: nenhuma ordem será enviada</AlertTitle>
          <AlertDescription>
            {data.kill_switch.reason ?? "Sem motivo informado."} Todos os controles de início estão
            bloqueados.
          </AlertDescription>
        </Alert>
      ) : null}
      {data !== undefined && !data.worker.alive ? (
        <Alert className="border-warning/40 text-warning">
          <CircleAlert className="size-4" aria-hidden="true" />
          <AlertTitle>Worker parado</AlertTitle>
          <AlertDescription>
            Os bots não estão avançando e os números abaixo estão desatualizados.
          </AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
