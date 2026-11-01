import { Card, CardContent, CardHeader, CardTitle } from "lost-ui/ui/card";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { useInterventions } from "@/hooks/bots/use-bots";
import { formatSignedPercent } from "@/lib/shared/format";
import { formatDateTime } from "@/lib/shared/dates";

const labels: Record<string, string> = {
  "bot.pause_requested": "Pausas",
  "bot.stop_requested": "Paradas",
  "bot.portfolio_reset": "Resets de portfólio",
  "bot.config_updated": "Alterações de configuração",
};

export function BotInterventions({ botId }: { botId: string }) {
  const query = useInterventions(botId);
  if (query.isError && query.data === undefined)
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  if (query.data === undefined) return <SkeletonBlock rows={3} />;
  const data = query.data;
  return (
    <Card>
      <CardHeader>
        <CardTitle>Intervenções nos últimos 30 dias</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        <p>
          {data.total} no total · {data.after_drawdown} depois de uma queda de pelo menos{" "}
          {data.drawdown_threshold_pct}%
        </p>
        {data.total === 0 ? (
          <p className="text-muted-foreground">Nenhuma intervenção: o plano está sendo seguido.</p>
        ) : null}
        <ul className="space-y-1">
          {Object.entries(data.by_type).map(([type, count]) => (
            <li key={type}>
              {labels[type] ?? type}: {count}
            </li>
          ))}
        </ul>
        <p className="text-muted-foreground">
          Kill switch neste período: {data.system.kill_switch_activated ?? 0} ativações ·{" "}
          {data.system.kill_switch_released ?? 0} liberações
        </p>
        <ol className="max-h-72 space-y-3 overflow-y-auto">
          {data.items.map((item, index) => (
            <li key={`${item.at}-${index}`} className="border-t pt-3">
              <p>
                {formatDateTime(item.at)} · {labels[item.type] ?? item.type} · {item.actor}
              </p>
              {item.reason ? <p className="text-muted-foreground">Motivo: {item.reason}</p> : null}
              <p className="text-muted-foreground">
                Drawdown:{" "}
                {item.drawdown_pct === null
                  ? "sem snapshot"
                  : formatSignedPercent(item.drawdown_pct)}
                %
              </p>
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}
