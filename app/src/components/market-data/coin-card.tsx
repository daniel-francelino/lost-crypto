import { CircleCheck, CircleX } from "lucide-react";
import { Card, CardContent, CardHeader } from "lost-ui/ui/card";
import { Switch } from "lost-ui/ui/switch";
import { Tooltip, TooltipContent, TooltipTrigger } from "lost-ui/ui/tooltip";
import { CoinIcon } from "@/components/shared/market-data/coin-icon";
import { TrendBadge } from "@/components/shared/status/trend-badge";
import { checkRows } from "@/lib/market-data/trend-checks";
import { formatUtcShort } from "@/lib/shared/dates";
import { TrendFrame } from "@/lib/shared/enums";
import { formatDecimal, formatSignedPercent } from "@/lib/shared/format";
import { exchangeLabel, trendFrameLabel, trendLabel } from "@/lib/shared/labels";
import { baseOf, displaySymbol } from "@/lib/shared/market-data/coins";
import type {
  RegisteredSymbol,
  SymbolTrends,
  TrendReading,
} from "@/lib/shared/market-data/registry.api";

const FRAME_ORDER = [TrendFrame.Week, TrendFrame.Day, TrendFrame.FourHours, TrendFrame.Hour];
const ICON = "size-5";

function StatusIcon({ active }: { active: boolean }) {
  const label = active ? "Ativa" : "Inativa";
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex" tabIndex={0}>
          {active ? (
            <CircleCheck className={`${ICON} text-success`} aria-hidden="true" />
          ) : (
            <CircleX className={`${ICON} text-destructive`} aria-hidden="true" />
          )}
          <span className="sr-only">{label}</span>
        </span>
      </TooltipTrigger>
      <TooltipContent>
        {active
          ? "Ativa: usada pelo sistema, com a tendência atualizada a cada fechamento de candle."
          : "Inativa: bots, backtests e importações não podem usar, e a tendência não é atualizada."}
      </TooltipContent>
    </Tooltip>
  );
}

function ReadingDetail({ reading }: { reading: TrendReading }) {
  return (
    <div className="space-y-1.5 text-xs">
      <p className="font-medium">
        {trendFrameLabel(reading.frame)} · {trendLabel(reading.trend)}
        {reading.confirmed ? " · confirmada" : ""}
      </p>
      {checkRows(reading).length === 0 ? (
        <p>Sem alinhamento das médias: não há tendência para confirmar.</p>
      ) : (
        <ul className="space-y-0.5">
          {checkRows(reading).map((row) => (
            <li key={row.label}>
              {row.label}: {row.text}
            </li>
          ))}
        </ul>
      )}
      <p>
        EMAs {formatSignedPercent(reading.ema_distance_pct)} · ADX {formatDecimal(reading.adx)}
      </p>
      <p className="opacity-80">Barra de {formatUtcShort(reading.bar_open_time)}</p>
    </div>
  );
}

function TrendTile({ frame, reading }: { frame: string; reading: TrendReading | undefined }) {
  return (
    <div className="space-y-1.5">
      <p className="text-xs text-muted-foreground">{trendFrameLabel(frame)}</p>
      {reading === undefined ? (
        <Tooltip>
          <TooltipTrigger asChild>
            <span className="text-sm text-muted-foreground" tabIndex={0}>
              —
            </span>
          </TooltipTrigger>
          <TooltipContent>
            Ainda sem leitura: o worker calcula no próximo fechamento.
          </TooltipContent>
        </Tooltip>
      ) : (
        <Tooltip>
          <TooltipTrigger asChild>
            <button type="button" className="rounded-md text-left">
              <TrendBadge trend={reading.trend} confirmed={reading.confirmed} />
            </button>
          </TooltipTrigger>
          <TooltipContent>
            <ReadingDetail reading={reading} />
          </TooltipContent>
        </Tooltip>
      )}
    </div>
  );
}

type CoinCardProps = {
  item: RegisteredSymbol;
  trends: SymbolTrends | undefined;
  canManage: boolean;
  pending: boolean;
  onToggle: (active: boolean) => void;
};

export function CoinCard({ item, trends, canManage, pending, onToggle }: CoinCardProps) {
  return (
    <Card className={item.active ? "" : "bg-muted/40"}>
      <CardHeader className="flex-row items-center gap-3 space-y-0">
        <CoinIcon symbol={item.symbol} size={40} />
        <div className="min-w-0 flex-1">
          <p className="text-base font-semibold leading-tight">{baseOf(item.symbol)}</p>
          <p className="truncate text-xs text-muted-foreground">
            {displaySymbol(item.symbol)} · {exchangeLabel(item.exchange)}
          </p>
        </div>
        <StatusIcon active={item.active} />
        {canManage ? (
          <Switch
            checked={item.active}
            disabled={pending}
            onCheckedChange={onToggle}
            aria-label={`${item.active ? "Desativar" : "Ativar"} ${displaySymbol(item.symbol)}`}
          />
        ) : null}
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-x-4 gap-y-3 sm:grid-cols-4">
          {FRAME_ORDER.map((frame) => (
            <TrendTile
              key={frame}
              frame={frame}
              reading={trends?.readings.find((entry) => entry.frame === frame)}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
