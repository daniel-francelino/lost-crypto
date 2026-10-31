import { ArrowDown, ArrowUp, Minus } from "lucide-react";
import { Sign, signOf } from "@/lib/shared/format";

const TONE: Record<Sign, string> = {
  [Sign.Positive]: "text-success",
  [Sign.Negative]: "text-destructive",
  [Sign.Zero]: "text-muted-foreground",
  [Sign.Unknown]: "text-muted-foreground",
};

type SignedValueProps = {
  raw: string | null | undefined;
  text: string;
  className?: string;
};

export function SignedValue({ raw, text, className = "" }: SignedValueProps) {
  const sign = signOf(raw);
  return (
    <span className={`inline-flex items-center gap-1 tabular-nums ${TONE[sign]} ${className}`}>
      {sign === Sign.Positive ? <ArrowUp className="size-3" aria-hidden="true" /> : null}
      {sign === Sign.Negative ? <ArrowDown className="size-3" aria-hidden="true" /> : null}
      {sign === Sign.Zero ? <Minus className="size-3" aria-hidden="true" /> : null}
      {text}
    </span>
  );
}
