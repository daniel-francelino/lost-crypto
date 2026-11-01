import type { Significance } from "@/lib/backtests/backtests.api";
import { formatInteger } from "@/lib/shared/format";

type RandomEntries = NonNullable<Significance["random_entries"]>;

export const RANDOM_ENTRIES_NOTE =
  "Este teste e o gaussiano do Sharpe definem acaso de jeitos diferentes e podem discordar. Valor-p não é a chance de a estratégia funcionar, e as entradas sorteadas podem se sobrepor.";

const REASONS: Record<string, string> = {
  "fewer than 10 completed trades": "Menos de 10 operações completas: o teste precisa de mais.",
};

export const unavailableText = (reason: string | null | undefined): string => {
  if (reason === null || reason === undefined) return "Teste não calculado.";
  const known = Object.entries(REASONS).find(([prefix]) => reason.startsWith(prefix));
  return known === undefined ? reason : known[1];
};

export const matchedText = (test: RandomEntries): string | null => {
  if (!test.available) return null;
  const { as_good_or_better: better, simulations } = test;
  if (
    better === null ||
    better === undefined ||
    simulations === null ||
    simulations === undefined
  ) {
    return null;
  }
  return `${formatInteger(better)} de ${formatInteger(simulations)} simulações com entradas aleatórias igualaram ou superaram este resultado.`;
};
