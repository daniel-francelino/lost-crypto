import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";
import { AppBackoffice } from "@/components/shared/layout/app-backoffice";
import { ensureSession } from "@/lib/shared/api/session";
import { AppRoute } from "@/lib/shared/routes";

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ location }) => {
    const user = await ensureSession();
    if (user === null) throw redirect({ to: AppRoute.Login, search: { redirect: location.href } });
  },
  component: AppLayout,
});

function AppLayout() {
  return (
    <AppBackoffice>
      <Outlet />
    </AppBackoffice>
  );
}
