import { createFileRoute } from "@tanstack/react-router";
import { ConnectionsPage } from "@/components/exchanges/connections-page";

export const Route = createFileRoute("/_app/exchanges/")({
  component: ConnectionsPage,
});
