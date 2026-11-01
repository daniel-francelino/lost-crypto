import { Card, CardContent, CardDescription, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import type { Significance } from "@/lib/backtests/backtests.api";
import { RANDOM_ENTRIES_NOTE, matchedText, unavailableText } from "@/lib/backtests/significance";
import { formatFraction, formatInteger } from "@/lib/shared/format";

export function SignificanceCard({ significance }: { significance: Significance | null }) {
  const test = significance?.random_entries ?? null;
  if (test === null) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Teste de entradas aleatórias</CardTitle>
        <CardDescription>
          Mesmo número de operações e mesma duração, com as entradas sorteadas nos preços
          observados.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {test.available ? (
          <>
            <p className="font-medium">{matchedText(test)}</p>
            <p className="text-muted-foreground">
              Fração: {formatFraction(test.fraction)} · {formatInteger(test.trades ?? 0)} operações
              · semente {test.seed ?? 0}. Quanto menor a fração, menos provável que seja sorte.
            </p>
          </>
        ) : (
          <p className="text-muted-foreground">{unavailableText(test.reason)}</p>
        )}
        <p className="text-muted-foreground">{RANDOM_ENTRIES_NOTE}</p>
      </CardContent>
    </Card>
  );
}
