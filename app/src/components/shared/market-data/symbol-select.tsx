import { useId } from "react";
import { FormField } from "lost-ui/forms/form-field";
import { Select, SelectContent, SelectItem, SelectTrigger } from "lost-ui/ui/select";
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
  const id = useId();
  const items = withCurrent(pairs.data ?? [], value).map((pair) => ({
    label: `${pair.base} · ${pair.name}`,
    value: pair.symbol,
  }));
  const selected = items.find((item) => item.value === value);
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
            <span className="truncate">{selected?.label ?? "Selecione um par"}</span>
          </span>
        </SelectTrigger>
        <SelectContent>
          {items.map((item) => (
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
