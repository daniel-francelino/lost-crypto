import { createFileRoute } from "@tanstack/react-router";
import { BotFormPage } from "@/components/bots/bot-form-page";
import { botPrefillSchema } from "@/lib/shared/bot-prefill";
import { Capability } from "@/lib/shared/capability";
import { requireCapability } from "@/lib/shared/route-guards";

export const Route = createFileRoute("/_app/bots/new")({
  validateSearch: botPrefillSchema,
  beforeLoad: () => requireCapability(Capability.BotsEdit),
  component: NewBotRoute,
});

function NewBotRoute() {
  const prefill = Route.useSearch();
  return <BotFormPage botId={null} prefill={prefill} />;
}
