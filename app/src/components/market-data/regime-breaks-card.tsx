import { useState } from "react";
import { Empty } from "lost-ui/data/empty";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import {
  useCreateRegimeBreak,
  useDeleteRegimeBreak,
  useRegimeBreaks,
} from "@/hooks/shared/use-regime-breaks";
import { useSessionUser } from "@/hooks/shared/use-session";
import { errorMessage } from "@/lib/shared/api/messages";
import { Capability, can } from "@/lib/shared/capability";
import { dayStartUtcIso, formatUtcDay, isDayString } from "@/lib/shared/dates";

const NAME_LIMIT = 60;

export function RegimeBreaksCard() {
  const user = useSessionUser();
  const query = useRegimeBreaks();
  const create = useCreateRegimeBreak();
  const remove = useDeleteRegimeBreak();
  const [name, setName] = useState("");
  const [day, setDay] = useState("");
  const [symbol, setSymbol] = useState("");
  const [note, setNote] = useState("");
  const valid = name.trim() !== "" && name.length <= NAME_LIMIT && isDayString(day);
  const submit = () =>
    create.mutate(
      {
        name: name.trim(),
        occurred_at: dayStartUtcIso(day),
        exchange: null,
        symbol: symbol.trim() === "" ? null : symbol.trim().toUpperCase(),
        note: note.trim() === "" ? null : note.trim(),
      },
      {
        onSuccess: () => {
          setName("");
          setDay("");
          setSymbol("");
          setNote("");
          toast.success("Quebra registrada.");
        },
        onError: (error) => toast.error(errorMessage(error)),
      },
    );
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Quebras de regime</CardTitle>
        <CardDescription>
          Datas que você nomeia (um colapso, uma mudança de regra). Registre as quebras antes de
          rodar os experimentos: cada uma guarda quando foi criada, e escolher a data depois de ver
          o resultado é liberdade de pesquisa. Não há edição: para corrigir, apague e crie de novo.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {can(user, Capability.MarketDataImport) ? (
          <div className="grid gap-3 sm:grid-cols-4">
            <input
              className="h-9 rounded-md border bg-background px-2 text-sm"
              aria-label="Nome da quebra"
              placeholder="Nome (ex.: colapso 2022)"
              maxLength={NAME_LIMIT}
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            <input
              className="h-9 rounded-md border bg-background px-2 text-sm"
              aria-label="Data da quebra"
              type="date"
              value={day}
              onChange={(event) => setDay(event.target.value)}
            />
            <input
              className="h-9 rounded-md border bg-background px-2 text-sm"
              aria-label="Par (vazio vale para todos)"
              placeholder="Par (vazio: todos)"
              value={symbol}
              onChange={(event) => setSymbol(event.target.value)}
            />
            <input
              className="h-9 rounded-md border bg-background px-2 text-sm"
              aria-label="Observação"
              placeholder="Observação (opcional)"
              maxLength={500}
              value={note}
              onChange={(event) => setNote(event.target.value)}
            />
            <div className="sm:col-span-4">
              <Button onClick={submit} disabled={!valid || create.isPending}>
                {create.isPending ? "Registrando…" : "Registrar quebra"}
              </Button>
            </div>
          </div>
        ) : null}
        <QueryBoundary query={query}>
          {(breaks) =>
            breaks.length === 0 ? (
              <Empty
                title="Nenhuma quebra cadastrada"
                description="Marque as datas antes de rodar os experimentos."
              />
            ) : (
              <ul className="space-y-2 text-sm" aria-label="Quebras de regime cadastradas">
                {breaks.map((item) => (
                  <li key={item.id} className="flex flex-wrap items-center justify-between gap-2">
                    <span>
                      <strong>{item.name}</strong> · {formatUtcDay(item.occurred_at)} UTC ·{" "}
                      {item.symbol ?? "todos os pares"} · criada por {item.created_by} em{" "}
                      {formatUtcDay(item.created_at)}
                      {item.note === null ? "" : ` · ${item.note}`}
                    </span>
                    {can(user, Capability.MarketDataImport) ? (
                      <Button
                        variant="outline"
                        size="sm"
                        disabled={remove.isPending}
                        onClick={() =>
                          remove.mutate(item.id, {
                            onError: (error) => toast.error(errorMessage(error)),
                          })
                        }
                      >
                        Apagar
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )
          }
        </QueryBoundary>
      </CardContent>
    </Card>
  );
}
