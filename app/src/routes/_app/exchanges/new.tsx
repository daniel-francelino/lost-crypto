import { createFileRoute } from "@tanstack/react-router";
import { ConnectionFormPage } from "@/components/exchanges/connection-form-page";
import { Capability } from "@/lib/shared/capability";
import { requireCapability } from "@/lib/shared/route-guards";

export const Route = createFileRoute("/_app/exchanges/new")({
  beforeLoad: () => requireCapability(Capability.ExchangesManage),
  component: ConnectionFormPage,
});
