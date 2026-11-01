import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "@tanstack/react-router";
import { useState } from "react";
import { Button } from "lost-ui/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import { toast } from "lost-ui/ui/sonner";
import { useRangeCoverage } from "@/hooks/shared/use-coverage";
import { type Backtest, createBacktest } from "@/lib/backtests/backtests.api";
import {
  hasStoredCandles,
  inputWithTimeframe,
  otherTimeframes,
} from "@/lib/backtests/other-timeframes";
import { errorMessage } from "@/lib/shared/api/messages";
import { QueryKey } from "@/lib/shared/api/query-keys";
import { Capability, can } from "@/lib/shared/capability";
import { dayString, toMs } from "@/lib/shared/dates";
import { AppRoute } from "@/lib/shared/routes";
import { useSessionUser } from "@/hooks/shared/use-session";

type OptionProps = {
  run: Backtest;
  timeframe: string;
  checked: boolean;
  onToggle: () => void;
};

function TimeframeOption({ run, timeframe, checked, onToggle }: OptionProps) {
  const coverage = useRangeCoverage({
    exchange: run.exchange,
    symbol: run.symbol,
    timeframe,
    start: dayString(toMs(run.start)),
    end: dayString(toMs(run.end)),
  });
  const stored = hasStoredCandles(coverage.data?.in_range?.present);
  return (
    <li className="flex flex-wrap items-center gap-2">
      <label className="flex items-center gap-2">
        <input type="checkbox" checked={checked} disabled={!stored} onChange={onToggle} />
        <span>{timeframe}</span>
      </label>
      {coverage.isPending ? (
        <span className="text-muted-foreground">verificando candles…</span>
      ) : stored ? null : (
        <span className="text-muted-foreground">
          sem candles armazenados neste período.{" "}
          <Link to={AppRoute.MarketData} className="underline">
            Importe em Dados de mercado
          </Link>
        </span>
      )}
    </li>
  );
}

export function CompareTimeframesCard({ run }: { run: Backtest }) {
  const user = useSessionUser();
  const navigate = useNavigate();
  const client = useQueryClient();
  const [chosen, setChosen] = useState<string[]>([]);
  const options = otherTimeframes(run.timeframe);
  const mutation = useMutation({
    mutationFn: (timeframes: string[]) =>
      Promise.all(
        timeframes.map((timeframe) => createBacktest(inputWithTimeframe(run, timeframe))),
      ),
    onSuccess: async (created) => {
      await client.invalidateQueries({ queryKey: QueryKey.Backtests.all() });
      toast.success("Execuções na fila; a comparação atualiza sozinha.");
      void navigate({
        to: AppRoute.BacktestsCompare,
        search: { ids: [run.id, ...created.map((item) => item.id)] },
      });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
  if (!can(user, Capability.BacktestsRun)) return null;
  const toggle = (timeframe: string) =>
    setChosen((current) =>
      current.includes(timeframe)
        ? current.filter((item) => item !== timeframe)
        : [...current, timeframe],
    );
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Comparar em outros intervalos</CardTitle>
        <CardDescription>
          A mesma configuração em candles menores. Intervalos curtos fazem mais operações, mas taxas
          e slippage dominam: confira a escada de custos de cada execução.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <ul className="space-y-2" aria-label="Intervalos para comparar">
          {options.map((timeframe) => (
            <TimeframeOption
              key={timeframe}
              run={run}
              timeframe={timeframe}
              checked={chosen.includes(timeframe)}
              onToggle={() => toggle(timeframe)}
            />
          ))}
        </ul>
        <Button
          onClick={() => mutation.mutate(chosen)}
          disabled={chosen.length === 0 || mutation.isPending}
        >
          {mutation.isPending ? "Criando…" : "Comparar"}
        </Button>
      </CardContent>
    </Card>
  );
}
