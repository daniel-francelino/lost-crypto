# Requests to the lost-ui library

> What Lost Crypto needs from `lost-ui` (`@danielsoaresf/lost-ui`) and does not find there. Each row says what the app does **today as a workaround**, so the workaround can be deleted when the request is done. Updated in place; never a second list. Format borrowed from aura-creative's `docs/lost-ui-requests.md`.

| ID | Request | Why the app needs it | Workaround today | Status |
|---|---|---|---|---|
| L1 | **Candlestick (OHLC) chart** with buy/sell markers and indicator overlays (EMA lines, Donchian channel) | A trading console reads price action, not only a closing line | `LineChart` of the close price (market data page); no trade markers | open |
| L2 | **Chart zoom / range brush**, and a Y-axis domain prop (not forced to start at 0) on `AreaChart` | Long equity curves; an equity curve that moves ±1% looks flat when the axis starts at 0 | Series are bounded by `limit`; the axis starts at 0 | open |
| L3 | **Stat tile** (label, value, delta, sign colour) | KPI rows on the dashboard, bot summary and metrics | `StatTile` in `components/shared/metrics` built from `Card` | open |
| L4 | **Status dot / live indicator** with an accessible label that honours reduced motion | Worker alive, mode badges | `Badge` with text and an icon | open |
| L5 | **Destructive button on dark mode keeps contrast.** `Button variant="destructive"` uses `dark:bg-destructive/60`; with a light-on-dark token set the `destructive-foreground` token fails WCAG AA on the blended colour (found by axe in the dark theme) | Kill switch and every destructive confirmation | `DangerButton` (`components/shared/feedback`) adds `dark:bg-destructive` | open |
| L6 | **String-valued money/number inputs.** `FormInputMoney` and `FormInputNumber` hold a `number`; money must stay a decimal string end to end | Capital, fees, risk limits | `FormInput` + `inputMode="decimal"` + validators in `lib/shared/validators.ts` | open |
| L7 | `LineChart` option `showYAxis` (it exists on `AreaChart` only) | Comparison charts need a value axis | none: comparison charts have no Y axis | open |
| L8 | `ProfilePage` with `onSaveName` optional (there is no editable name here) | The profile screen only changes the password | A page of our own built from `Card` and `FormInputPassword` | open |
| L9 | Sorting a column by a custom comparer should not need numeric parsing in the app | Sweep results sorted by a decimal-string return | `compare` + `compareDecimal` in `lib/shared/format.ts` | open |

## Heatmap chart (requested 2026-10-31)

**Need:** the sweep page shows, for 2-parameter grids, a cross table of results (rows = one parameter, columns = the other) to tell a plateau from an isolated peak (book 1 ch. 3, O7). Today it is a plain `<table>` with token tints in `components/backtests/robustness-card.tsx`.

**Ask:** a `HeatmapChart` in `lost-ui/charts` driven by props: `rows`, `columns`, `value(row, column)`, a diverging scale around zero from tokens, a formatter, an optional marked cell (the winner), tooltips and an accessible table fallback. State must not rely on colour alone (show the value).
