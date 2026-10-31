import { createFileRoute } from "@tanstack/react-router";
import { BotsPage } from "@/components/bots/bots-page";

export const Route = createFileRoute("/_app/bots/")({
  component: BotsPage,
});
