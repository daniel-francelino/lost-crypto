import { FormInput } from "lost-ui/forms/form-input";
import { type ParamValues, validateParam } from "@/lib/shared/strategies/params";
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
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {strategy.parameters.map((param) => (
        <FormInput
          key={`${strategy.type_key}-${param.name}`}
          label={param.name}
          description={param.description}
          inputMode="decimal"
          disabled={disabled}
          required={param.default !== null}
          value={values[param.name] ?? ""}
          onValueChange={(value) => onChange(param.name, value)}
          rules={[(value) => validateParam(param, value ?? "")]}
        />
      ))}
    </div>
  );
}
