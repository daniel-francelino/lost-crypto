import {
  Activity,
  Bot,
  ClipboardList,
  Database,
  FlaskConical,
  KeyRound,
  LayoutDashboard,
  ShieldCheck,
  UserCog,
  Users,
} from "lucide-react";
import type { NavItem, NavSection } from "lost-ui/app/app-nav";
import type { User } from "@/lib/shared/api/schemas";
import { Capability, can } from "@/lib/shared/capability";
import { AppRoute } from "@/lib/shared/routes";

const icon = (Component: typeof Bot) => <Component aria-hidden="true" />;

export const navigation = (user: User | null): NavSection[] => {
  const usersItem: NavItem = {
    title: "Usuários",
    to: AppRoute.Users,
    icon: icon(Users),
    hidden: !can(user, Capability.UsersManage),
  };
  return [
    {
      label: "Visão geral",
      items: [{ title: "Painel", to: AppRoute.Home, exact: true, icon: icon(LayoutDashboard) }],
    },
    {
      label: "Operação",
      items: [
        { title: "Bots", to: AppRoute.Bots, icon: icon(Bot) },
        { title: "Conexões", to: AppRoute.Exchanges, icon: icon(KeyRound) },
      ],
    },
    {
      label: "Pesquisa",
      items: [
        { title: "Backtests", to: AppRoute.Backtests, icon: icon(FlaskConical) },
        { title: "Dados de mercado", to: AppRoute.MarketData, icon: icon(Database) },
      ],
    },
    {
      label: "Sistema",
      items: [
        { title: "Status", to: AppRoute.System, icon: icon(Activity) },
        { title: "Auditoria", to: AppRoute.Audit, icon: icon(ClipboardList) },
      ],
    },
    {
      label: "Configurações",
      items: [{ title: "Meu perfil", to: AppRoute.Profile, icon: icon(UserCog) }, usersItem],
    },
  ];
};

export const bottomNavigation: NavItem[] = [
  { title: "Painel", to: AppRoute.Home, exact: true, icon: icon(LayoutDashboard) },
  { title: "Bots", to: AppRoute.Bots, icon: icon(Bot) },
  { title: "Backtests", to: AppRoute.Backtests, icon: icon(FlaskConical) },
  { title: "Status", to: AppRoute.System, icon: icon(ShieldCheck) },
];
