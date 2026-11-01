import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { type NoteTarget, addNote, listNotes } from "@/lib/shared/audit/audit.api";

export const useNotes = (entityId: string) =>
  useQuery({
    queryKey: QueryKey.Audit.notes(entityId),
    queryFn: ({ signal }) => listNotes(entityId, signal),
  });

export const useAddNote = (target: NoteTarget, entityId: string) => {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (text: string) => addNote(target, entityId, text),
    onSuccess: async () => {
      await client.invalidateQueries({ queryKey: QueryKey.Audit.notes(entityId) });
      await client.invalidateQueries({ queryKey: QueryKey.Audit.all() });
    },
  });
};
