import { PageHeader } from "lost-ui/app/page-header";
import { Badge } from "lost-ui/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "lost-ui/ui/card";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { UpdatedAt } from "@/components/shared/feedback/updated-at";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import { useCapabilities, useSystemStatus } from "@/hooks/shared/use-system";
import { formatAge, formatDateTime } from "@/lib/shared/dates";
import { botStateLabel } from "@/lib/shared/labels";

const secondsOrNull = (value: number | null): number | null =>
  value === null ? null : Math.round(value);

export function SystemPage() {
  const status = useSystemStatus();
  const capabilities = useCapabilities();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Status do sistema"
        description="Worker, bots, kill switch e o que este ambiente permite."
        actions={<UpdatedAt updatedAtMs={status.dataUpdatedAt} failed={status.isError} />}
      />
      <QueryBoundary query={status}>
        {(data) => (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <StatTile
                label="Worker"
                value={data.worker.alive ? "Ativo" : "Parado"}
                hint={`Heartbeat ${formatAge(secondsOrNull(data.worker.age_seconds))}`}
              />
              <StatTile
                label="Kill switch"
                value={data.kill_switch.active ? "ATIVO" : "Liberado"}
                hint={
                  data.kill_switch.active
                    ? `${data.kill_switch.reason ?? "Sem motivo"} · ${formatDateTime(data.kill_switch.changed_at)}`
                    : `Última mudança: ${formatDateTime(data.kill_switch.changed_at)}`
                }
              />
              <StatTile label="Exchanges registradas" value={data.exchanges.join(", ") || "—"} />
              <StatTile label="Bots sem heartbeat" value={String(data.stale_bots.length)} />
            </div>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Bots por estado</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-2">
                {Object.entries(data.bots_by_state).map(([state, count]) => (
                  <Badge key={state} variant="secondary">
                    {botStateLabel(state)}: {count}
                  </Badge>
                ))}
              </CardContent>
            </Card>
            {data.stale_bots.length === 0 ? null : (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">Bots que não estão avançando</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-1 text-sm">
                    {data.stale_bots.map((bot) => (
                      <li key={bot.bot_id}>
                        <strong>{bot.name}</strong> — último heartbeat{" "}
                        {formatAge(secondsOrNull(bot.age_seconds))}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </QueryBoundary>
      <QueryBoundary query={capabilities}>
        {(data) => (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">O que este ambiente permite</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2">
                <dt className="text-muted-foreground">Ambiente do servidor</dt>
                <dd>{data.environment}</dd>
                <dt className="text-muted-foreground">Testnet habilitado</dt>
                <dd>{data.testnet_trading_enabled ? "Sim" : "Não"}</dd>
                <dt className="text-muted-foreground">Live habilitado</dt>
                <dd>{data.live_trading_enabled ? "Sim" : "Não"}</dd>
                <dt className="text-muted-foreground">Live disponível</dt>
                <dd>{data.live_available ? "Sim" : "Não"}</dd>
                <dt className="text-muted-foreground">Dias mínimos de paper</dt>
                <dd>{data.live_min_paper_days}</dd>
                <dt className="text-muted-foreground">Validade da aprovação live</dt>
                <dd>{data.live_approval_minutes} min</dd>
                <dt className="text-muted-foreground">Estratégias</dt>
                <dd>{data.strategies.join(", ")}</dd>
              </dl>
              {data.live_blockers.length === 0 ? null : (
                <div>
                  <p className="font-medium">O que falta para o live:</p>
                  <ul className="list-disc pl-5 text-muted-foreground">
                    {data.live_blockers.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}
              <p className="text-xs text-muted-foreground">
                Visão do processo da API; o worker confere a própria configuração a cada ciclo.
              </p>
            </CardContent>
          </Card>
        )}
      </QueryBoundary>
    </div>
  );
}
