import { Link } from "@tanstack/react-router";
import { Bot as BotIcon } from "lucide-react";
import { PageHeader } from "lost-ui/app/page-header";
import { EmptyState as Empty } from "@/components/shared/feedback/empty-state";
import { Card, CardContent, CardHeader } from "lost-ui/ui/card";
import { IconCardTitle as CardTitle } from "@/components/shared/metrics/icon-card-title";
import { QueryBoundary } from "@/components/shared/feedback/query-boundary";
import { UpdatedAt } from "@/components/shared/feedback/updated-at";
import { StatTile } from "@/components/shared/metrics/stat-tile";
import { BotStateBadge, ModeBadge } from "@/components/shared/status/badges";
import { SymbolLabel } from "@/components/shared/market-data/coin-icon";
import { SignedValue } from "@/components/shared/status/signed-value";
import { useSummary } from "@/hooks/bots/use-bots";
import { useOverview } from "@/hooks/shared/use-overview";
import type { BotOverview, PortfolioSummary } from "@/lib/bots/bots.api";
import { TradingProduct } from "@/lib/shared/enums";
import { ageSeconds, formatAge } from "@/lib/shared/dates";
import {
  formatInteger,
  formatMoney,
  formatPrice,
  formatSignedMoney,
  formatSignedPercent,
  quoteCurrency,
} from "@/lib/shared/format";
import { modeLabel } from "@/lib/shared/labels";

function SummaryGroup({ group }: { group: PortfolioSummary }) {
  return (
    <section className="space-y-2" aria-label={`${modeLabel(group.mode)} ${group.quote_currency}`}>
      <h2 className="flex items-center gap-2 text-sm font-semibold">
        <ModeBadge mode={group.mode} />
        <span className="text-muted-foreground">{group.quote_currency}</span>
      </h2>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
        <StatTile label="Capital" value={formatMoney(group.equity, group.quote_currency)} />
        <StatTile
          label="Retorno"
          value={
            <SignedValue raw={group.return_pct} text={formatSignedPercent(group.return_pct)} />
          }
        />
        <StatTile
          label="Resultado realizado"
          value={
            <SignedValue
              raw={group.realized_pnl}
              text={formatSignedMoney(group.realized_pnl, group.quote_currency)}
            />
          }
        />
        <StatTile label="Taxas" value={formatMoney(group.fees_paid, group.quote_currency)} />
        <StatTile label="Bots rodando" value={`${group.running} / ${group.bots}`} />
        <StatTile label="Posições abertas" value={formatInteger(group.open_positions)} />
      </div>
    </section>
  );
}

function BotCard({ bot }: { bot: BotOverview }) {
  const quote = quoteCurrency(bot.symbol);
  const isFutures = bot.product === TradingProduct.LinearPerpetual;
  return (
    <Card>
      <CardHeader className="space-y-2 pb-2">
        <CardTitle className="text-base" icon={BotIcon}>
          <Link
            to="/bots/$botId"
            params={{ botId: bot.id }}
            search={{}}
            className="underline-offset-4 hover:underline"
          >
            {bot.name}
          </Link>
        </CardTitle>
        <div className="flex flex-wrap items-center gap-2">
          <ModeBadge mode={bot.mode} />
          <BotStateBadge state={bot.observed_state} />
          <span className="inline-flex items-center gap-2 text-xs text-muted-foreground">
            <SymbolLabel symbol={bot.symbol} size={18} />
            <span>· {bot.timeframe}</span>
          </span>
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-2 gap-2 text-sm">
        <span className="text-muted-foreground">Capital</span>
        <span className="text-right tabular-nums">{formatMoney(bot.equity, quote)}</span>
        <span className="text-muted-foreground">Retorno</span>
        <span className="text-right">
          <SignedValue raw={bot.return_pct} text={formatSignedPercent(bot.return_pct)} />
        </span>
        <span className="text-muted-foreground">Posição</span>
        <span className="text-right">
          {bot.in_position
            ? isFutures
              ? bot.position_side === "short"
                ? "Short"
                : "Long"
              : "Comprado"
            : "Fora"}
        </span>
        <span className="text-muted-foreground">
          {isFutures ? "Mark price" : "\u00daltimo pre\u00e7o"}
        </span>
        <span className="text-right tabular-nums">{formatPrice(bot.last_price)}</span>
        {isFutures && (
          <>
            <span className="text-muted-foreground">Alavancagem / margem</span>
            <span className="text-right tabular-nums">
              {bot.leverage ?? 1}× · {formatMoney(bot.isolated_margin ?? "0", quote)}
            </span>
            <span className="text-muted-foreground">PnL não realizado</span>
            <span className="text-right">
              <SignedValue
                raw={bot.unrealized_pnl ?? "0"}
                text={formatSignedMoney(bot.unrealized_pnl ?? "0", quote)}
              />
            </span>
            <span className="text-muted-foreground">
              {bot.liquidation_price_source === "exchange_reported"
                ? "Liquida\u00e7\u00e3o (Binance)"
                : "Liquida\u00e7\u00e3o estimada"}
            </span>
            <span className="text-right tabular-nums">
              {formatPrice(bot.liquidation_price ?? null)}
            </span>
            <span className="text-muted-foreground">Funding pago / recebido</span>
            <span className="text-right tabular-nums">
              {formatMoney(bot.funding_paid ?? "0", quote)} /{" "}
              {formatMoney(bot.funding_received ?? "0", quote)}
            </span>
          </>
        )}
        <span className="text-muted-foreground">Heartbeat</span>
        <span className="text-right">{formatAge(ageSeconds(bot.last_heartbeat_at))}</span>
        <span className="text-muted-foreground">Intervenções (30 d)</span>
        <span className="text-right tabular-nums">{formatInteger(bot.interventions_30d)}</span>
      </CardContent>
    </Card>
  );
}

export function Dashboard() {
  const summary = useSummary();
  const overview = useOverview();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Painel"
        description="Visão geral dos bots e do sistema."
        actions={<UpdatedAt updatedAtMs={overview.dataUpdatedAt} failed={overview.isError} />}
      />
      <QueryBoundary query={summary}>
        {(groups) =>
          groups.length === 0 ? null : (
            <div className="space-y-4">
              {groups.map((group) => (
                <SummaryGroup key={`${group.mode}-${group.quote_currency}`} group={group} />
              ))}
            </div>
          )
        }
      </QueryBoundary>
      <QueryBoundary query={overview}>
        {(bots) =>
          bots.length === 0 ? (
            <Empty
              title="Você ainda não tem bots"
              description="Crie um bot em paper trading para começar."
            />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {bots.map((bot) => (
                <BotCard key={bot.id} bot={bot} />
              ))}
            </div>
          )
        }
      </QueryBoundary>
    </div>
  );
}
