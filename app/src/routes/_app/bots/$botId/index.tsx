import { createFileRoute } from "@tanstack/react-router";
import { z } from "zod";
import { BotDetailPage } from "@/components/bots/bot-detail-page";
import { BotTab } from "@/lib/bots/tabs";

export const Route = createFileRoute("/_app/bots/$botId/")({
  validateSearch: z.object({ tab: z.nativeEnum(BotTab).optional().catch(undefined) }),
  component: BotDetailRoute,
});

function BotDetailRoute() {
  const { botId } = Route.useParams();
  const { tab } = Route.useSearch();
  const navigate = Route.useNavigate();

  return (
    <BotDetailPage
      botId={botId}
      tab={tab ?? BotTab.Summary}
      onTabChange={(next) => void navigate({ search: { tab: next }, replace: true })}
    />
  );
}
