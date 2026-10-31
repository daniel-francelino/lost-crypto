import type { ReactNode } from "react";
import { Card, CardContent } from "lost-ui/ui/card";

type StatTileProps = { label: string; value: ReactNode; hint?: ReactNode };

export function StatTile({ label, value, hint }: StatTileProps) {
  return (
    <Card>
      <CardContent className="space-y-1 p-4">
        <p className="text-xs font-medium text-muted-foreground">{label}</p>
        <p className="text-xl font-semibold tabular-nums">{value}</p>
        {hint === undefined ? null : <p className="text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  );
}
