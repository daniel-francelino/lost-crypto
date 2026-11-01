export const WINDOW_PARAM_BY_STRATEGY: Record<string, string> = {
  mean_reversion_zscore: "lookback",
};

export const windowParamOf = (strategyType: string): string | null =>
  WINDOW_PARAM_BY_STRATEGY[strategyType] ?? null;

export const windowsText = (windows: readonly number[] | undefined): string | null =>
  windows === undefined || windows.length === 0 ? null : windows.join(", ");

export const gridValue = (windows: readonly number[]): string => windows.join(", ");
