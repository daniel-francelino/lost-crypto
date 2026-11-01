import { Zap } from "lucide-react";
import { PageHeader } from "lost-ui/app/page-header";
import { Alert, AlertDescription, AlertTitle } from "lost-ui/ui/alert";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "lost-ui/ui/tabs";
import { DiagnosisTab, ParityTab } from "@/components/bots/bot-execution";
import { BotControls } from "@/components/bots/bot-controls";
import { BotInterventions } from "@/components/bots/bot-interventions";
import {
  ConfigTab,
  OrdersTab,
  PerformanceTab,
  SignalsTab,
  SummaryTab,
} from "@/components/bots/bot-tabs";
import { AuditTable } from "@/components/shared/audit/audit-table";
import { NotesPanel } from "@/components/shared/notes/notes-panel";
import { NoteTarget } from "@/lib/shared/audit/audit.api";
import { ErrorBlock, SkeletonBlock } from "@/components/shared/feedback/query-boundary";
import { UpdatedAt } from "@/components/shared/feedback/updated-at";
import { BotStateBadge, ModeBadge } from "@/components/shared/status/badges";
import { SymbolLabel } from "@/components/shared/market-data/coin-icon";
import { isConverging, useBot } from "@/hooks/bots/use-bots";
import { useNow } from "@/hooks/shared/use-now";
import { useSystemStatus } from "@/hooks/shared/use-system";
import { BOT_TAB_LABELS, BotTab } from "@/lib/bots/tabs";
import { ageSeconds, formatAge } from "@/lib/shared/dates";
import { BotState, ExecutionMode } from "@/lib/shared/enums";
import { botStateLabel } from "@/lib/shared/labels";

const STALE_HEARTBEAT_SECONDS = 600;

type BotDetailPageProps = { botId: string; tab: BotTab; onTabChange: (tab: BotTab) => void };

export function BotDetailPage({ botId, tab, onTabChange }: BotDetailPageProps) {
  const query = useBot(botId);
  const status = useSystemStatus();
  const now = useNow();

  if (query.isError && query.data === undefined) {
    return <ErrorBlock error={query.error} onRetry={() => void query.refetch()} />;
  }
  const bot = query.data;
  if (bot === undefined) return <SkeletonBlock rows={5} />;

  const converging = isConverging(bot.desired_state, bot.observed_state);
  const heartbeat = ageSeconds(bot.last_heartbeat_at, now);
  const stale =
    bot.observed_state === BotState.Running &&
    (status.data?.worker.alive === false ||
      (heartbeat !== null && heartbeat > STALE_HEARTBEAT_SECONDS));
  const isLive = bot.mode === ExecutionMode.Live;

  return (
    <div className="space-y-4">
      <PageHeader
        title={
          <span className="flex flex-wrap items-center gap-2">
            {bot.name}
            <ModeBadge mode={bot.mode} />
            <BotStateBadge state={bot.observed_state} />
          </span>
        }
        description={
          <span className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <SymbolLabel symbol={bot.symbol} size={18} />
            <span>
              · {bot.timeframe} · {bot.strategy_type}
            </span>
          </span>
        }
        actions={<BotControls bot={bot} />}
      />
      {isLive ? (
        <Alert className="border-live/60">
          <Zap className="size-4 text-live" aria-hidden="true" />
          <AlertTitle>Dinheiro real</AlertTitle>
          <AlertDescription>
            Este bot opera na conta live. Cada início exige uma nova aprovação.
          </AlertDescription>
        </Alert>
      ) : null}
      {converging ? (
        <Alert>
          <AlertTitle>
            {`Aguardando o worker: pedido "${botStateLabel(bot.desired_state)}", estado atual "${botStateLabel(bot.observed_state)}".`}
          </AlertTitle>
        </Alert>
      ) : null}
      {bot.last_error === null ? null : (
        <Alert variant="destructive">
          <AlertTitle>Último erro</AlertTitle>
          <AlertDescription>{bot.last_error}</AlertDescription>
        </Alert>
      )}
      {stale ? (
        <Alert className="border-warning/40 text-warning">
          <AlertTitle>Dados desatualizados</AlertTitle>
          <AlertDescription>
            O worker não está avançando este bot ({formatAge(heartbeat)}). Os números podem estar
            parados.
          </AlertDescription>
        </Alert>
      ) : null}
      <BotInterventions botId={bot.id} />
      <div className="text-xs text-muted-foreground">
        Heartbeat {formatAge(heartbeat)} ·{" "}
        <UpdatedAt updatedAtMs={query.dataUpdatedAt} failed={query.isError} />
      </div>
      <Tabs value={tab} onValueChange={(value) => onTabChange(value as BotTab)}>
        <TabsList className="flex-wrap">
          {Object.values(BotTab).map((item) => (
            <TabsTrigger key={item} value={item}>
              {BOT_TAB_LABELS[item]}
            </TabsTrigger>
          ))}
        </TabsList>
        <TabsContent value={BotTab.Summary} className="pt-4">
          <SummaryTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Orders} className="pt-4">
          <OrdersTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Signals} className="pt-4">
          <SignalsTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Performance} className="pt-4">
          <PerformanceTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Parity} className="pt-4">
          <ParityTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Diagnosis} className="pt-4">
          <DiagnosisTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Config} className="pt-4">
          <ConfigTab bot={bot} />
        </TabsContent>
        <TabsContent value={BotTab.Audit} className="pt-4">
          <div className="space-y-6">
            <NotesPanel target={NoteTarget.Bot} entityId={bot.id} />
            <AuditTable botId={bot.id} />
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
