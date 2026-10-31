import { Outlet, createFileRoute } from "@tanstack/react-router";
import { AppBackoffice } from "@/components/shared/layout/app-backoffice";

export const Route = createFileRoute("/_app")({
  component: AppLayout,
});

function AppLayout() {
  return (
    <AppBackoffice>
      <Outlet />
    </AppBackoffice>
  );
}
