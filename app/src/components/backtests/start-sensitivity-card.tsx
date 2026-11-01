import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "lost-ui/ui/card";
import type { Sweep } from "@/lib/backtests/backtests.api";
import { type Spread, startSensitivity } from "@/lib/backtests/start-sensitivity";
import { formatInteger, formatSignedPercent } from "@/lib/shared/format";

const ROWS: { key: keyof Spread; label: string }[] = [
  { key: "min", label: "Mínimo" },
  { key: "median", label: "Mediana (inferior)" },
  { key: "max", label: "Máximo" },
];

export function StartSensitivityCard({ sweep }: { sweep: Sweep }) {
  const result = startSensitivity(sweep);
  if (result === null) return null;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Dispersão pela data inicial</CardTitle>
        <CardDescription>
          A mesma configuração começando em dias diferentes. Leia como dispersão, não como valor
          esperado: uma faixa larga indica que o resultado depende do dia em que começou.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="text-muted-foreground">
          {formatInteger(result.runs)} execuções concluídas. Deslocar o início também muda o
          aquecimento da estratégia e a primeira operação.
        </p>
        <table className="w-full text-left">
          <caption className="sr-only">Retorno e drawdown entre as datas iniciais</caption>
          <thead>
            <tr className="text-muted-foreground">
              <th className="py-1 pr-3" />
              <th className="py-1 pr-3">Retorno</th>
              <th className="py-1 pr-3">Drawdown máximo</th>
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.key}>
                <th className="py-1 pr-3 font-medium">{row.label}</th>
                <td className="py-1 pr-3">{formatSignedPercent(result.returnPct?.[row.key])}</td>
                <td className="py-1 pr-3">{formatSignedPercent(result.drawdownPct?.[row.key])}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardContent>
    </Card>
  );
}
