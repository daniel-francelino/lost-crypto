import { useNow } from "@/hooks/shared/use-now";
import { ageSecondsSinceMs, formatAge } from "@/lib/shared/dates";

type UpdatedAtProps = { updatedAtMs: number; failed?: boolean };

export function UpdatedAt({ updatedAtMs, failed = false }: UpdatedAtProps) {
  const now = useNow();
  if (updatedAtMs === 0) return null;
  const seconds = ageSecondsSinceMs(updatedAtMs, now);
  return (
    <span className={`text-xs ${failed ? "text-warning" : "text-muted-foreground"}`}>
      {failed ? "Desatualizado · " : ""}
      Atualizado {formatAge(seconds)}
    </span>
  );
}
