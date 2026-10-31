import { LayoutDashboard } from "lucide-react";
import type { NavSection } from "lost-ui/app/app-nav";
import { AppRoute } from "@/lib/shared/routes";

export const navigation: NavSection[] = [
  {
    label: "Visão geral",
    items: [
      {
        title: "Painel",
        to: AppRoute.Home,
        exact: true,
        icon: <LayoutDashboard aria-hidden="true" />,
      },
    ],
  },
];
