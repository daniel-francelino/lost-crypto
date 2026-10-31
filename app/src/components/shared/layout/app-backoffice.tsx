import { useRouterState } from "@tanstack/react-router";
import type { ReactNode } from "react";
import { BackofficeLayout } from "lost-ui/templates/backoffice/backoffice-layout";
import { Toaster } from "lost-ui/ui/sonner";
import { navigation } from "@/components/shared/layout/nav-config";
import { renderLink } from "@/components/shared/layout/render-link";

export function AppBackoffice({ children }: { children: ReactNode }) {
  const pathname = useRouterState({ select: (state) => state.location.pathname });

  return (
    <BackofficeLayout
      sections={navigation}
      pathname={pathname}
      renderLink={renderLink}
      logo={<span className="px-2 text-base font-semibold tracking-tight">Lost Crypto</span>}
      transitionKey={pathname}
      overlay={<Toaster position="top-right" />}
    >
      {children}
    </BackofficeLayout>
  );
}
