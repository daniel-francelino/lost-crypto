import type { ReactNode } from "react";
import {
  Activity,
  BarChart3,
  Bot,
  Brain,
  CalendarDays,
  ChartNoAxesCombined,
  CircleHelp,
  Database,
  Fingerprint,
  KeyRound,
  ListChecks,
  Network,
  Receipt,
  Shield,
  SlidersHorizontal,
  TrendingUp,
  UserRound,
  Wallet,
  type LucideIcon,
} from "lucide-react";
import { CardTitle } from "lost-ui/ui/card";

function iconForTitle(title: ReactNode): LucideIcon {
  const text =
    typeof title === "string"
      ? title
          .normalize("NFD")
          .replace(/\p{Diacritic}/gu, "")
          .toLowerCase()
      : "";
  if (text.includes("estrat") || text.includes("parametro")) return Brain;
  if (text.includes("robust") || text.includes("risco") || text.includes("segur")) return Shield;
  if (text.includes("dados") || text.includes("fechamento")) return Database;
  if (text.includes("periodo") || text.includes("cobertura")) {
    return CalendarDays;
  }
  if (text.includes("capital") || text.includes("dimension") || text.includes("tamanho")) {
    return Wallet;
  }
  if (text.includes("custo") || text.includes("taxa")) return Receipt;
  if (text.includes("signific") || text.includes("aleat")) return BarChart3;
  if (text.includes("sharpe") || text.includes("sortino")) return Activity;
  if (text.includes("regime") || text.includes("resultado")) return TrendingUp;
  if (text.includes("qualidade") || text.includes("execu")) return Activity;
  if (text.includes("paridade") || text.includes("reprodu")) return Fingerprint;
  if (text.includes("triagem") || text.includes("ordem")) return ListChecks;
  if (text.includes("mercado") || text.includes("exchange")) return Network;
  if (text.includes("perfil") || text.includes("usuario")) return UserRound;
  if (text.includes("senha") || text.includes("chave")) return KeyRound;
  if (text.includes("bot")) return Bot;
  if (text.includes("curva") || text.includes("compar")) return ChartNoAxesCombined;
  if (text.includes("movimento") || text.includes("meia-vida") || text.includes("hurst")) {
    return Activity;
  }
  if (text.includes("monitor")) return Activity;
  if (text.includes("config") || text.includes("ambiente")) return SlidersHorizontal;
  return CircleHelp;
}

export function IconCardTitle({
  icon: Icon,
  children,
  className,
}: {
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
}) {
  const TitleIcon = Icon ?? iconForTitle(children);
  return (
    <CardTitle className={className}>
      <span className="flex items-center gap-2.5">
        <span
          aria-hidden="true"
          className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/8 text-primary"
        >
          <TitleIcon className="size-4" strokeWidth={1.8} />
        </span>
        <span>{children}</span>
      </span>
    </CardTitle>
  );
}
