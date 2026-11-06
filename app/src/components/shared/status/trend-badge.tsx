import { BadgeCheck, Minus, TrendingDown, TrendingUp } from "lucide-react";
import { Badge } from "lost-ui/ui/badge";
import { Trend } from "@/lib/shared/enums";
import { trendLabel } from "@/lib/shared/labels";

const ICON = "size-3";
const TONE_BULLISH = "border-success/40 bg-success/10 text-success";
const TONE_BEARISH = "border-destructive/40 bg-destructive/10 text-destructive";
const TONE_SIDEWAYS = "border-border bg-muted text-muted-foreground";

const tone = (trend: string) => {
  if (trend === Trend.Bullish) {
    return { className: TONE_BULLISH, icon: <TrendingUp className={ICON} aria-hidden="true" /> };
  }
  if (trend === Trend.Bearish) {
    return { className: TONE_BEARISH, icon: <TrendingDown className={ICON} aria-hidden="true" /> };
  }
  return { className: TONE_SIDEWAYS, icon: <Minus className={ICON} aria-hidden="true" /> };
};

type TrendBadgeProps = { trend: string; confirmed?: boolean };

export function TrendBadge({ trend, confirmed = false }: TrendBadgeProps) {
  const { className, icon } = tone(trend);
  return (
    <Badge variant="outline" className={`gap-1 ${className}`}>
      {icon}
      {trendLabel(trend)}
      {confirmed ? (
        <>
          <BadgeCheck className={ICON} aria-hidden="true" />
          <span className="sr-only">confirmada</span>
        </>
      ) : null}
    </Badge>
  );
}
