import type { UseQueryResult } from "@tanstack/react-query";
import { TriangleAlert } from "lucide-react";
import type { ReactNode } from "react";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Button } from "lost-ui/ui/button";
import { Skeleton } from "lost-ui/ui/skeleton";
import { errorMessage } from "@/lib/shared/api/messages";

type QueryBoundaryProps<T> = {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  skeleton?: ReactNode;
};

export function SkeletonBlock({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Carregando">
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton key={index} className="h-10 w-full" />
      ))}
    </div>
  );
}

export function ErrorBlock({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  return (
    <Alert variant="destructive">
      <TriangleAlert className="size-4" aria-hidden="true" />
      <AlertTitle>Não foi possível carregar</AlertTitle>
      <AlertDescription className="flex flex-wrap items-center gap-3">
        <span>{errorMessage(error)}</span>
        <Button size="sm" variant="outline" onClick={onRetry}>
          Tentar de novo
        </Button>
      </AlertDescription>
    </Alert>
  );
}

export function StaleNotice({ error }: { error: unknown }) {
  return (
    <Alert className="border-warning/40 text-warning">
      <TriangleAlert className="size-4" aria-hidden="true" />
      <AlertTitle>Dados desatualizados</AlertTitle>
      <AlertDescription>
        A última atualização falhou ({errorMessage(error)}). Os números abaixo podem estar
        defasados.
      </AlertDescription>
    </Alert>
  );
}

export function QueryBoundary<T>({ query, children, skeleton }: QueryBoundaryProps<T>) {
  if (query.data !== undefined) {
    return (
      <div className="space-y-3">
        {query.isError ? <StaleNotice error={query.error} /> : null}
        {children(query.data)}
      </div>
    );
  }
  if (query.isError) return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  return <>{skeleton ?? <SkeletonBlock />}</>;
}
