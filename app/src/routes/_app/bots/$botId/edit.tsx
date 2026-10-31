import { createFileRoute } from "@tanstack/react-router";
import { BotFormPage } from "@/components/bots/bot-form-page";
import { Capability } from "@/lib/shared/capability";
import { requireCapability } from "@/lib/shared/route-guards";

export const Route = createFileRoute("/_app/bots/$botId/edit")({
  beforeLoad: () => requireCapability(Capability.BotsEdit),
  component: EditBotRoute,
});

function EditBotRoute() {
  const { botId } = Route.useParams();
  return <BotFormPage botId={botId} />;
}
