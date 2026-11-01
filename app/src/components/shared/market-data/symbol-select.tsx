import { FormSelect } from "lost-ui/forms/form-select";
import { CoinIcon } from "@/components/shared/market-data/coin-icon";
import { useSupportedPairs } from "@/hooks/shared/use-supported-pairs";
import { withCurrent } from "@/lib/shared/market-data/coins";

type Props = {
  value: string;
  onValueChange: (value: string) => void;
  label?: string;
  required?: boolean | undefined;
  errorMessage?: string | undefined;
  className?: string | undefined;
};

export function SymbolSelect({
  value,
  onValueChange,
  label = "Par",
  required = false,
  errorMessage = "",
  className = "",
}: Props) {
  const pairs = useSupportedPairs();
  const items = withCurrent(pairs.data ?? [], value).map((pair) => ({
    label: `${pair.base} · ${pair.name}`,
    value: pair.symbol,
    text: pair.symbol,
    icon: <CoinIcon symbol={pair.symbol} />,
  }));
  return (
    <FormSelect
      label={label}
      required={required}
      className={className}
      items={items}
      value={value}
      onValueChange={onValueChange}
      errorMessage={errorMessage}
    />
  );
}
