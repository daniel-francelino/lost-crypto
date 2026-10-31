import { useQueryClient } from "@tanstack/react-query";
import { useNavigate, useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { BackofficeLayout } from "lost-ui/templates/backoffice/backoffice-layout";
import { Toaster } from "lost-ui/ui/sonner";
import { breadcrumbsFor } from "@/components/shared/layout/breadcrumbs";
import { bottomNavigation, navigation } from "@/components/shared/layout/nav-config";
import { renderLink } from "@/components/shared/layout/render-link";
import { SafetyStrip, SystemBanners } from "@/components/shared/layout/safety-strip";
import { useSessionUser } from "@/hooks/shared/use-session";
import { logout } from "@/lib/shared/api/session";
import { roleLabel } from "@/lib/shared/labels";
import { AppRoute } from "@/lib/shared/routes";

const userItems = [{ title: "Meu perfil", to: AppRoute.Profile }];

export function AppBackoffice({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });
  const user = useSessionUser();
  const client = useQueryClient();
  const navigate = useNavigate();

  const signOut = async () => {
    await logout();
    client.clear();
    await navigate({ to: AppRoute.Login });
  };

  return (
    <BackofficeLayout
      sections={navigation(user)}
      pathname={pathname}
      renderLink={renderLink}
      logo={<span className="px-2 text-base font-semibold tracking-tight">Lost Crypto</span>}
      {...(user === null
        ? {}
        : { user: { name: user.username, description: roleLabel(user.role) } })}
      userItems={userItems}
      onSignOut={() => void signOut()}
      breadcrumbs={breadcrumbsFor(pathname)}
      bottomItems={bottomNavigation}
      topbarActions={<SafetyStrip />}
      transitionKey={pathname}
      overlay={<Toaster position="top-right" />}
    >
      <div className="space-y-4">
        <SystemBanners />
        {children}
      </div>
    </BackofficeLayout>
  );
}
