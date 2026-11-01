import type { ReactNode } from "react";
import {
  Activity,
  ArrowLeftRight,
  Bot,
  BriefcaseBusiness,
  ChartNoAxesCombined,
  Gauge,
  Network,
  Percent,
  Receipt,
  Shield,
  Tag,
  Target,
  TrendingDown,
  TrendingUp,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { Card, CardContent } from "lost-ui/ui/card";

type StatTileProps = { label: string; value: ReactNode; hint?: ReactNode };

function iconForLabel(label: string): LucideIcon {
  const text = label
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
  if (text.includes("drawdown") || text.includes("volatilidade")) return TrendingDown;
  if (text.includes("retorno")) return TrendingUp;
  if (text.includes("capital") || text.includes("equity") || text.includes("caixa")) return Wallet;
  if (text.includes("resultado") || text.includes("pnl") || text.includes("lucro")) {
    return ChartNoAxesCombined;
  }
  if (text.includes("taxa de acerto") || text.includes("significancia")) return Target;
  if (text.includes("taxa") || text.includes("fee")) return Receipt;
  if (text.includes("posicao")) return BriefcaseBusiness;
  if (text.includes("preco")) return Tag;
  if (text.includes("risco") || text.includes("stop") || text.includes("protegida")) {
    return Shield;
  }
  if (text.includes("worker") || text.includes("heartbeat") || text.includes("latencia")) {
    return Activity;
  }
  if (text.includes("exchange")) return Network;
  if (text.includes("bot")) return Bot;
  if (text.includes("ordem") || text.includes("execucao") || text.includes("fill")) {
    return ArrowLeftRight;
  }
  if (text.includes("sharpe") || text.includes("sortino") || text.includes("information")) {
    return Gauge;
  }
  if (text.includes("percent") || text.includes("volume")) return Percent;
  return ChartNoAxesCombined;
}

export function StatTile({ label, value, hint }: StatTileProps) {
  const Icon = iconForLabel(label);
  return (
    <Card className="h-full border-border/70 transition-colors hover:border-primary/30">
      <CardContent className="relative flex h-full min-h-28 flex-col gap-1 p-4 pr-14">
        <span
          aria-hidden="true"
          className="absolute right-4 top-4 grid size-8 place-items-center rounded-lg bg-primary/8 text-primary"
        >
          <Icon className="size-4" strokeWidth={1.8} />
        </span>
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="break-words text-xl font-semibold tabular-nums">{value}</p>
        {hint === undefined ? null : (
          <p className="text-xs leading-relaxed text-muted-foreground">{hint}</p>
        )}
      </CardContent>
    </Card>
  );
}
