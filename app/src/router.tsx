import { QueryClient } from "@tanstack/react-query";
import { createRouter } from "@tanstack/react-router";
import { AppErrorPage, AppNotFoundPage } from "@/components/shared/layout/route-fallbacks";
import { routeTree } from "./routeTree.gen";

export const getRouter = () => {
  const queryClient = new QueryClient();

  return createRouter({
    routeTree,
    context: { queryClient },
    scrollRestoration: true,
    defaultPreloadStaleTime: 0,
    defaultErrorComponent: AppErrorPage,
    defaultNotFoundComponent: AppNotFoundPage,
    defaultPendingMs: 150,
    defaultPendingMinMs: 250,
  });
};

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof getRouter>;
  }
}
