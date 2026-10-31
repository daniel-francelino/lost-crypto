import {
  CircleAlert,
  CircleCheck,
  CircleHelp,
  CirclePause,
  CircleStop,
  FileText,
  FlaskConical,
  Hourglass,
  Zap,
} from "lucide-react";
import type { ReactNode } from "react";
import { Badge } from "lost-ui/ui/badge";
import {
  AlertSeverity,
  BotState,
  ConnectionStatus,
  ExecutionMode,
  JobStatus,
  OrderStatus,
  Side,
  Unknown,
} from "@/lib/shared/enums";
import {
  alertSeverityLabel,
  botStateLabel,
  connectionStatusLabel,
  environmentLabel,
  jobStatusLabel,
  modeLabel,
  orderStatusLabel,
  sideLabel,
} from "@/lib/shared/labels";

const ICON = "size-3";
const TONE_SUCCESS = "border-success/40 bg-success/10 text-success";
const TONE_WARNING = "border-warning/40 bg-warning/10 text-warning";
const TONE_DANGER = "border-destructive/40 bg-destructive/10 text-destructive";
const TONE_NEUTRAL = "border-border bg-muted text-muted-foreground";
const TONE_LIVE = "border-transparent bg-live text-live-foreground";

type Tone = { className: string; icon: ReactNode };

const tag = (tone: Tone, label: string) => (
  <Badge variant="outline" className={`gap-1 ${tone.className}`}>
    {tone.icon}
    {label}
  </Badge>
);

const botStateTone = (value: string): Tone => {
  if (value === BotState.Running) {
    return { className: TONE_SUCCESS, icon: <CircleCheck className={ICON} aria-hidden="true" /> };
  }
  if (value === BotState.Paused) {
    return { className: TONE_WARNING, icon: <CirclePause className={ICON} aria-hidden="true" /> };
  }
  if (value === BotState.Error) {
    return { className: TONE_DANGER, icon: <CircleAlert className={ICON} aria-hidden="true" /> };
  }
  if (value === BotState.Stopped) {
    return { className: TONE_NEUTRAL, icon: <CircleStop className={ICON} aria-hidden="true" /> };
  }
  return { className: TONE_NEUTRAL, icon: <CircleHelp className={ICON} aria-hidden="true" /> };
};

export function BotStateBadge({ state }: { state: string }) {
  return tag(botStateTone(state), botStateLabel(state));
}

export function ModeBadge({ mode }: { mode: string }) {
  if (mode === ExecutionMode.Live) {
    return (
      <Badge variant="outline" className={`gap-1 font-semibold ${TONE_LIVE}`}>
        <Zap className={ICON} aria-hidden="true" />
        {modeLabel(mode)}
      </Badge>
    );
  }
  if (mode === ExecutionMode.Testnet) {
    return (
      <Badge variant="secondary" className="gap-1">
        <FlaskConical className={ICON} aria-hidden="true" />
        {modeLabel(mode)}
      </Badge>
    );
  }
  return (
    <Badge variant="outline" className="gap-1">
      <FileText className={ICON} aria-hidden="true" />
      {mode === ExecutionMode.Paper ? modeLabel(mode) : environmentLabel(mode)}
    </Badge>
  );
}

export function OrderStatusBadge({ status }: { status: string }) {
  if (status === OrderStatus.Filled) {
    return tag({ className: TONE_SUCCESS, icon: null }, orderStatusLabel(status));
  }
  if (status === OrderStatus.Rejected || status === OrderStatus.Unknown) {
    return tag({ className: TONE_DANGER, icon: null }, orderStatusLabel(status));
  }
  if (status === OrderStatus.Submitting || status === OrderStatus.Open) {
    return tag({ className: TONE_WARNING, icon: null }, orderStatusLabel(status));
  }
  return tag({ className: TONE_NEUTRAL, icon: null }, orderStatusLabel(status));
}

export function JobStatusBadge({ status }: { status: string }) {
  if (status === JobStatus.Completed) {
    return tag({ className: TONE_SUCCESS, icon: null }, jobStatusLabel(status));
  }
  if (status === JobStatus.Failed) {
    return tag({ className: TONE_DANGER, icon: null }, jobStatusLabel(status));
  }
  if (status === JobStatus.Running || status === JobStatus.Queued) {
    return tag(
      { className: TONE_WARNING, icon: <Hourglass className={ICON} aria-hidden="true" /> },
      jobStatusLabel(status),
    );
  }
  return tag({ className: TONE_NEUTRAL, icon: null }, jobStatusLabel(status));
}

export function ConnectionStatusBadge({ status }: { status: string }) {
  if (status === ConnectionStatus.Active) {
    return tag({ className: TONE_SUCCESS, icon: null }, connectionStatusLabel(status));
  }
  if (status === ConnectionStatus.Invalid) {
    return tag({ className: TONE_DANGER, icon: null }, connectionStatusLabel(status));
  }
  if (status === ConnectionStatus.Pending) {
    return tag({ className: TONE_WARNING, icon: null }, connectionStatusLabel(status));
  }
  return tag({ className: TONE_NEUTRAL, icon: null }, connectionStatusLabel(status));
}

export function AlertSeverityBadge({ severity }: { severity: string }) {
  if (severity === AlertSeverity.Critical) {
    return tag(
      { className: TONE_DANGER, icon: <CircleAlert className={ICON} aria-hidden="true" /> },
      alertSeverityLabel(severity),
    );
  }
  if (severity === AlertSeverity.Warning) {
    return tag(
      { className: TONE_WARNING, icon: <CircleAlert className={ICON} aria-hidden="true" /> },
      alertSeverityLabel(severity),
    );
  }
  return tag(
    { className: TONE_NEUTRAL, icon: <CircleHelp className={ICON} aria-hidden="true" /> },
    alertSeverityLabel(severity),
  );
}

export function SideBadge({ side }: { side: string }) {
  const tone = side === Side.Buy ? TONE_SUCCESS : side === Side.Sell ? TONE_DANGER : TONE_NEUTRAL;
  return tag({ className: tone, icon: null }, side === Unknown ? "—" : sideLabel(side));
}
