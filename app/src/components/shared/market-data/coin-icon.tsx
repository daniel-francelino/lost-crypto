import { useState } from "react";
import { coinIconSources, coinInitial } from "@/lib/shared/market-data/coins";

type IconProps = { symbol: string; size?: number | undefined };

export function CoinIcon({ symbol, size = 24 }: IconProps) {
  const [failures, setFailures] = useState(0);
  const sources = coinIconSources(symbol);
  const source = sources[failures];
  const style = { width: size, height: size, borderRadius: "50%" };
  return source === undefined ? (
    <span
      aria-hidden="true"
      style={style}
      className="inline-flex shrink-0 items-center justify-center bg-muted text-xs font-medium"
    >
      {coinInitial(symbol)}
    </span>
  ) : (
    <img
      src={source}
      alt=""
      aria-hidden="true"
      loading="lazy"
      style={style}
      className="shrink-0 rounded-[50%] bg-muted object-contain"
      referrerPolicy="no-referrer"
      onError={() => setFailures((count) => count + 1)}
    />
  );
}

export function SymbolLabel({ symbol, size }: IconProps) {
  return (
    <span className="inline-flex items-center gap-2">
      <CoinIcon symbol={symbol} size={size} />
      <span>{symbol}</span>
    </span>
  );
}
