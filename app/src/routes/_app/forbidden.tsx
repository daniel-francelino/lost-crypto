import { createFileRoute } from "@tanstack/react-router";
import { ForbiddenPage } from "lost-ui/templates/errors/forbidden-page";
import { renderLink } from "@/components/shared/layout/render-link";
import { AppRoute } from "@/lib/shared/routes";

export const Route = createFileRoute("/_app/forbidden")({
  component: () => <ForbiddenPage homeHref={AppRoute.Home} renderLink={renderLink} />,
});
