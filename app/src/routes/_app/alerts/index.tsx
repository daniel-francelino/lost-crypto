import { createFileRoute } from "@tanstack/react-router";
import { AlertsPage } from "@/components/system/alerts-page";

export const Route = createFileRoute("/_app/alerts/")({
  component: AlertsPage,
});
