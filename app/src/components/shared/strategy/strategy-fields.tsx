import { FormInputNumber } from "lost-ui/forms/form-input-number";
import { numberText, numberValue } from "@/lib/shared/format";
import { type ParamValues, validateParam } from "@/lib/shared/strategies/params";
import { stopHints } from "@/lib/shared/strategies/stop-hint";
import type { Strategy } from "@/lib/shared/strategies/strategies.api";

type StrategyFieldsProps = {
  strategy: Strategy | undefined;
  values: ParamValues;
  onChange: (name: string, value: string) => void;
  disabled?: boolean;
};

export function StrategyFields({
  strategy,
  values,
  onChange,
  disabled = false,
}: StrategyFieldsProps) {
  if (strategy === undefined) return null;
  const hints = stopHints(strategy.style, values);
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {strategy.parameters.map((param) => (
        <FormInputNumber
          key={`${strategy.type_key}-${param.name}`}
          label={param.name}
          description={param.description}
          showControls={false}
          step={param.type === "integer" ? 1 : 0.1}
          {...(param.minimum === null ? {} : { min: param.minimum })}
          disabled={disabled}
          required={param.default !== null}
          value={numberValue(values[param.name] ?? "")}
          onValueChange={(value) => onChange(param.name, numberText(value))}
          rules={[(value) => validateParam(param, value === null ? "" : String(value))]}
        />
      ))}
      {hints.map((hint) => (
        <p key={hint} className="text-sm text-muted-foreground sm:col-span-2">
          {hint}
        </p>
      ))}
    </div>
  );
}
