import { Link } from "@tanstack/react-router";
import { Bell } from "lucide-react";
import { Badge } from "lost-ui/ui/badge";
import { useAlertSummary } from "@/hooks/shared/use-alerts";
import { AppRoute } from "@/lib/shared/routes";

const ICON = "size-3";
const TONE_DANGER = "border-destructive/40 bg-destructive/10 text-destructive";
const TONE_WARNING = "border-warning/40 bg-warning/10 text-warning";

const alertTone = (critical: boolean, unread: boolean): string => {
  if (critical) return TONE_DANGER;
  return unread ? TONE_WARNING : "";
};

export function AlertsIndicator() {
  const summary = useAlertSummary();
  const data = summary.data;
  if (data === undefined) return null;
  const critical = data.critical_open > 0;
  const label = data.unread === 0 ? "Sem alertas novos" : `${data.unread} alertas não lidos`;

  return (
    <Link to={AppRoute.Alerts} title="Alertas" aria-label={label}>
      <Badge variant="outline" className={`gap-1 ${alertTone(critical, data.unread > 0)}`}>
        <Bell className={ICON} aria-hidden="true" />
        <span className="hidden sm:inline">Alertas</span>
        {data.unread > 0 ? <span>{data.unread}</span> : null}
        {critical ? <span className="hidden sm:inline">· crítico</span> : null}
      </Badge>
    </Link>
  );
}
