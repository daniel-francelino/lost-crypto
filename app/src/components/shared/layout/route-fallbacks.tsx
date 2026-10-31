import { ErrorFallback } from "lost-ui/templates/errors/error-fallback";
import { NotFoundPage } from "lost-ui/templates/errors/not-found-page";
import { renderLink } from "@/components/shared/layout/render-link";
import { AppRoute } from "@/lib/shared/routes";

export function AppErrorPage({ reset }: { reset: () => void }) {
  return <ErrorFallback onRetry={reset} homeHref={AppRoute.Home} renderLink={renderLink} />;
}

export function AppNotFoundPage() {
  return <NotFoundPage homeHref={AppRoute.Home} renderLink={renderLink} />;
}
