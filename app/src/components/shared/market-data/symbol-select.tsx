import { useId } from "react";
import { FormField } from "lost-ui/forms/form-field";
import { Select, SelectContent, SelectItem, SelectTrigger } from "lost-ui/ui/select";
import { CoinIcon } from "@/components/shared/market-data/coin-icon";
import { useRegisteredSymbols } from "@/hooks/shared/use-symbol-registry";
import { useSupportedPairs } from "@/hooks/shared/use-supported-pairs";
import { baseOf, coinName, quoteOf, withCurrent } from "@/lib/shared/market-data/coins";
import { ExchangeId, TradingProduct } from "@/lib/shared/enums";

type Props = {
  value: string;
  onValueChange: (value: string) => void;
  label?: string;
  required?: boolean | undefined;
  errorMessage?: string | undefined;
  className?: string | undefined;
  exchange?: string | undefined;
  product?: string | undefined;
};

export function SymbolSelect({
  value,
  onValueChange,
  label = "Par",
  required = false,
  errorMessage = "",
  className = "",
  exchange = ExchangeId.Binance,
  product = TradingProduct.Spot,
}: Props) {
  const registry = useRegisteredSymbols();
  const pairs = useSupportedPairs();
  const id = useId();
  const available = (registry.data ?? [])
    .filter((item) => item.active && item.exchange === exchange)
    .map((item) => ({
      symbol: item.symbol,
      base: baseOf(item.symbol),
      quote: quoteOf(item.symbol),
      name: coinName(item.symbol, pairs.data),
    }));
  const options = withCurrent(available, value).map((pair) => ({
    label:
      product === TradingProduct.Spot
        ? `${pair.base} · ${pair.name}`
        : `${pair.base} · perp (${pair.quote})`,
    value: pair.symbol,
  }));
  const selected = options.find((item) => item.value === value);
  return (
    <FormField
      label={label}
      required={required}
      className={className}
      errorMessage={errorMessage}
      invalid={Boolean(errorMessage)}
      ids={{
        id,
        labelId: `${id}-label`,
        descriptionId: `${id}-description`,
        helpId: `${id}-help`,
        errorId: `${id}-error`,
      }}
    >
      <Select value={value} onValueChange={onValueChange} required={required}>
        <SelectTrigger id={id} aria-invalid={Boolean(errorMessage)} className="w-full">
          <span className="flex min-w-0 items-center gap-2">
            {selected ? <CoinIcon symbol={selected.value} size={20} /> : null}
            <span className="truncate">
              {selected?.label ??
                (options.length === 0 ? "Nenhuma moeda cadastrada" : "Selecione um par")}
            </span>
          </span>
        </SelectTrigger>
        <SelectContent>
          {options.map((item) => (
            <SelectItem key={item.value} value={item.value}>
              <span className="flex items-center gap-2">
                <CoinIcon symbol={item.value} size={20} />
                <span>{item.label}</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </FormField>
  );
}
