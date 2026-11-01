import { useState } from "react";
import { Empty } from "lost-ui/data/empty";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { useAddNote, useNotes } from "@/hooks/shared/use-notes";
import { useSessionUser } from "@/hooks/shared/use-session";
import { errorMessage } from "@/lib/shared/api/messages";
import type { NoteTarget } from "@/lib/shared/audit/audit.api";
import { Capability, can } from "@/lib/shared/capability";
import { formatDateTime } from "@/lib/shared/dates";
import { NOTE_MAX_LENGTH, canSubmitNote, remainingCharacters } from "@/lib/shared/notes";

type NotesPanelProps = { target: NoteTarget; entityId: string };

export function NotesPanel({ target, entityId }: NotesPanelProps) {
  const user = useSessionUser();
  const [text, setText] = useState("");
  const query = useNotes(entityId);
  const mutation = useAddNote(target, entityId);
  const submit = () =>
    mutation.mutate(text, {
      onSuccess: () => {
        setText("");
        toast.success("Nota registrada.");
      },
      onError: (error) => toast.error(errorMessage(error)),
    });
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Notas de análise</CardTitle>
        <CardDescription>
          Registre por que esta estratégia foi pausada ou aposentada e o que você concluiu. Fica na
          auditoria, com autor e data.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {can(user, Capability.BotsEdit) ? (
          <div className="space-y-2">
            <textarea
              className="min-h-24 w-full rounded-md border bg-background p-2 text-sm"
              aria-label="Nova nota de análise"
              maxLength={NOTE_MAX_LENGTH}
              value={text}
              onChange={(event) => setText(event.target.value)}
            />
            <div className="flex items-center justify-between gap-3">
              <span className="text-xs text-muted-foreground">
                {remainingCharacters(text)} caracteres restantes
              </span>
              <Button onClick={submit} disabled={!canSubmitNote(text) || mutation.isPending}>
                {mutation.isPending ? "Registrando…" : "Registrar nota"}
              </Button>
            </div>
          </div>
        ) : null}
        <QueryBoundary query={query}>
          {(page) =>
            page.data.length === 0 ? (
              <Empty
                title="Nenhuma nota ainda"
                description="Registre por que esta estratégia foi pausada ou aposentada."
              />
            ) : (
              <ul className="space-y-3" aria-label="Notas registradas">
                {page.data.map((note, index) => (
                  <li key={`${note.occurred_at ?? "sem-data"}-${index}`} className="text-sm">
                    <p className="text-xs text-muted-foreground">
                      {note.actor} · {formatDateTime(note.occurred_at)}
                    </p>
                    <p className="whitespace-pre-wrap">{String(note.payload["text"] ?? "")}</p>
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
