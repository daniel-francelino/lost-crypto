import { Outlet, createFileRoute, redirect } from "@tanstack/react-router";
import { AppBackoffice } from "@/components/shared/layout/app-backoffice";
import { ApiError } from "@/lib/shared/api/api-error";
import { ensureSession } from "@/lib/shared/api/session";
import { AppRoute } from "@/lib/shared/routes";

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ location }) => {
    let user;
    try {
      user = await ensureSession();
    } catch (error) {
      if (!(error instanceof ApiError) || !error.isNetwork) throw error;
      user = null;
    }
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
