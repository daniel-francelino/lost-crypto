import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { Input } from "lost-ui/ui/input";
import { useSizing } from "@/hooks/backtests/use-backtests";
import type { Backtest } from "@/lib/backtests/backtests.api";
import { formatUtc } from "@/lib/shared/dates";
import {
  compareDecimal,
  formatFractionAsPercent,
  formatInteger,
  formatPercent,
  formatRatio,
} from "@/lib/shared/format";
import { JobStatus } from "@/lib/shared/enums";
import { prefillFromRun } from "@/lib/shared/bot-prefill";
import { Capability, can } from "@/lib/shared/capability";
import { useSessionUser } from "@/hooks/shared/use-session";
import { AppRoute } from "@/lib/shared/routes";

export function SizingCard({ run }: { run: Backtest }) {
  const user = useSessionUser();
  const [tolerable, setTolerable] = useState("10");
  const [scope, setScope] = useState<"day" | "bar">("day");
  const ready =
    run.status === JobStatus.Completed &&
    run.tail_risk != null &&
    /^\d+(\.\d+)?$/.test(tolerable) &&
    compareDecimal(tolerable, "0") > 0 &&
    compareDecimal(tolerable, "100") <= 0;
  const query = useSizing(run.id, tolerable, scope, ready);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Referência de dimensionamento</CardTitle>
        <CardDescription>
          Estimativa histórica consultiva. Não altera ordens nem prevê perdas futuras.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4 text-sm">
        {run.tail_risk == null ? (
          <p>Este resultado não contém os dados de risco necessários. Rode o backtest novamente.</p>
        ) : null}
        <div className="flex flex-wrap items-end gap-3">
          <label className="grid gap-1">
            Perda tolerável por período (%)
            <Input
              type="number"
              min="0.01"
              max="100"
              step="0.1"
              value={tolerable}
              onChange={(event) => setTolerable(event.target.value)}
            />
          </label>
          <label className="grid gap-1">
            Período
            <select
              className="h-10 rounded-md border bg-background px-3"
              value={scope}
              onChange={(event) => setScope(event.target.value as "day" | "bar")}
            >
              <option value="day">Dia UTC</option>
              <option value="bar">Barra</option>
            </select>
          </label>
        </div>
        {query.isPending && ready ? <p>Calculando referência…</p> : null}
        {query.isError ? <p role="alert">Não foi possível calcular. Tente novamente.</p> : null}
        {query.data ? (
          <>
            <dl className="grid gap-2 sm:grid-cols-2">
              <div>
                <dt className="text-muted-foreground">Kelly cheio / meio Kelly</dt>
                <dd>
                  {query.data.kelly
                    ? `${formatRatio(query.data.kelly.full)} / ${formatRatio(query.data.kelly.half)}`
                    : "Amostra insuficiente"}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Fração máxima sugerida</dt>
                <dd className="font-semibold">
                  {formatFractionAsPercent(query.data.suggested_max_position_fraction)} · limite:{" "}
                  {query.data.binding}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Pior perda da estratégia</dt>
                <dd>
                  {formatPercent(query.data.tail?.strategy_worst_loss_pct)}
                  {query.data.tail?.strategy_at
                    ? ` · ${formatUtc(query.data.tail.strategy_at)}`
                    : ""}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Pior perda do ativo</dt>
                <dd>
                  {formatPercent(query.data.tail?.asset_worst_loss_pct)}
                  {query.data.tail?.asset_at ? ` · ${formatUtc(query.data.tail.asset_at)}` : ""}
                </dd>
              </div>
              <div>
                <dt className="text-muted-foreground">Retornos na amostra</dt>
                <dd>
                  {formatInteger(query.data.sample.returns)} ·{" "}
                  {formatInteger(query.data.sample.gaps)} lacunas
                </dd>
              </div>
            </dl>
            {query.data.above_reference ? (
              <p className="rounded-md border border-warning p-3">
                A fração configurada está acima desta referência histórica.
              </p>
            ) : null}
            {can(user, Capability.BotsEdit) &&
            compareDecimal(query.data.suggested_max_position_fraction, "0") > 0 ? (
              <Link
                className="inline-flex h-9 items-center rounded-md border px-3 font-medium hover:bg-accent"
                to={AppRoute.BotsNew}
                search={prefillFromRun(run, query.data.suggested_max_position_fraction)}
              >
                Criar bot com a fração sugerida
              </Link>
            ) : null}
            <ul className="list-disc space-y-1 pl-5 text-muted-foreground">
              {query.data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </>
        ) : null}
      </CardContent>
    </Card>
  );
}
