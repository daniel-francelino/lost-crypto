import { AppRoute } from "@/lib/shared/routes";

type Crumb = { label: string; to?: string };

const LABELS: Record<string, string> = {
  bots: "Bots",
  new: "Novo",
  backtests: "Backtests",
  compare: "Comparar",
  sweeps: "Varredura",
  "market-data": "Dados de mercado",
  exchanges: "Conexões",
  audit: "Auditoria",
  system: "Status",
  settings: "Configurações",
  profile: "Meu perfil",
  users: "Usuários",
};

const ROUTES: Record<string, string> = {
  bots: AppRoute.Bots,
  backtests: AppRoute.Backtests,
  "market-data": AppRoute.MarketData,
  exchanges: AppRoute.Exchanges,
  audit: AppRoute.Audit,
  system: AppRoute.System,
};

export const breadcrumbsFor = (pathname: string): Crumb[] => {
  const segments = pathname.split("/").filter((part) => part !== "");
  const crumbs: Crumb[] = [{ label: "Início", to: AppRoute.Home }];
  segments.forEach((segment, index) => {
    const last = index === segments.length - 1;
    const label = LABELS[segment] ?? "Detalhe";
    const to = last ? undefined : ROUTES[segment];
    crumbs.push(to === undefined ? { label } : { label, to });
  });
  return pathname === AppRoute.Home ? [] : crumbs;
};
