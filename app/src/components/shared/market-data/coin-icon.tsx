import { useState } from "react";
import { coinIconSrc, coinInitial } from "@/lib/shared/market-data/coins";

type IconProps = { symbol: string; size?: number | undefined };

export function CoinIcon({ symbol, size = 20 }: IconProps) {
  const [failed, setFailed] = useState(false);
  const style = { width: size, height: size };
  return failed ? (
    <span
      aria-hidden="true"
      style={style}
      className="inline-flex shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium"
    >
      {coinInitial(symbol)}
    </span>
  ) : (
    <img
      src={coinIconSrc(symbol)}
      alt=""
      aria-hidden="true"
      loading="lazy"
      style={style}
      className="shrink-0 rounded-full"
      onError={() => setFailed(true)}
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
