# 07 — UX rules for a trading console

Adapted from aura-creative's interface rules (UI-1…UI-14) plus what is specific to an app that can lose real money. Rule IDs below are Lost Crypto's own (prefix `UX-`); the aura rule they come from is noted.

## 1. Never let the screen lie

| ID | Rule |
|---|---|
| UX-1 | **Freshness is visible.** Anything polled shows when it was last updated. When the worker is not alive, a bot heartbeat is old, or a request failed, the numbers are marked **stale** (muted + a "desatualizado" badge) — they are never shown as if live |
| UX-2 | **Desired ≠ observed.** Commands answer 202; show both states and report success only when `observed_state` matches. An `error` state shows `last_error` |
| UX-3 | **No optimistic updates for anything that touches a bot, an order, a connection or the kill switch.** Wait for the server, then invalidate and refetch. (Optimistic UI is allowed for purely local preferences.) |
| UX-4 | **Money is never computed or rounded in the browser** (F5). A value that is not available is "—", never `0` |
| UX-5 | **Unknown is visible.** An enum value the app does not know (`OrderStatus.UNKNOWN`, a state added by a newer backend) renders as a labelled "desconhecido" badge, not as a crash or a blank |
| UX-6 | **Simulated results are labelled.** Backtest and paper numbers say "simulado" next to the headline figure; testnet says "testnet"; only live is unlabelled-by-default and carries the live treatment below |

## 2. Live-money safeguards in the UI

The backend refuses unsafe actions; the UI's job is to make it *hard to do the dangerous thing by accident* and *impossible to mistake which mode you are in*.

| ID | Rule |
|---|---|
| UX-7 | **Mode is always shown, in the same place and style**: a `Badge` with text and an icon — `PAPER`, `TESTNET`, `LIVE` — on every bot card, row, detail header, order list and confirmation dialog. `LIVE` uses its own reserved token (`--live`), used for nothing else, and is never conveyed by colour alone |
| UX-8 | **A live bot's detail page looks different** (persistent banner "Dinheiro real"), so the operator cannot confuse it with a paper bot of the same name and symbol |
| UX-9 | **Live actions are never one click.** Start, resume after pause/kill switch, promote and approve go through the flow in [06](06-screens.md#6-live-promotion-and-approval--inside-bot-detail); the confirmation requires typing the exact bot name; the token is single-use and shown with a countdown |
| UX-10 | **No live action from lists, the dashboard or shortcuts.** Bulk actions, if ever added, exclude live bots |
| UX-11 | **Destructive buttons name the target**: "Parar bot *ema-btc-1h*", not "Confirmar". Confirmation dialogs (`AlertDialog`) state the consequence ("posição aberta será mantida; stops nativos continuam na exchange") |
| UX-12 | **A refusal from the backend is shown verbatim** in the dialog that caused it (422 string). It is the explanation; the UI does not paraphrase safety messages |
| UX-13 | Secrets (API key/secret, confirmation tokens) never appear in the URL, the cache, storage, logs or error reports; see [05](05-authentication.md#exchange-keys) |
| UX-14 | The environment (`local` / `prod`) is visible in the shell; a `prod` build with the API on `localhost`, or the reverse, shows a blocking warning |

### Kill switch

* Always reachable from the top bar (admin). Activation is **fast**: one button + a confirmation that includes an optional reason, because stopping must be easier than starting.
* Release is **deliberate**: a dialog that shows why it was activated (`reason`, `changed_at`) and asks for a reason to release. Never a toggle.
* When active, a persistent banner on every screen ("Kill switch ativo: nenhuma ordem será enviada") and all start/resume controls are disabled with that reason.
* Viewers see the state, never the control.

## 3. State coverage (aura UI-2, UI-3, UI-5)

Every screen and list implements **skeleton → error with retry → empty → no results → data**. Skeletons keep the final height. Errors keep the layout and offer a way out; a failed polling refetch keeps the last data visible with the stale mark (UX-1) instead of replacing it with an error.

Forms: validation on the client (`rules`, zod) **and** the server (422 mapped to fields); required fields marked; hints for format/limits; focus the first invalid field; the submit button is `loading` and disabled (no double submit); typed data survives a failure; unsaved-changes warning on leaving a dirty form. Success toast only **after** the server confirms.

## 4. Display rules

* **Numbers:** through `format.ts` only ([04](04-api-client.md#money-and-numbers)). Right-aligned, tabular figures, fixed decimals per asset (quantity decimals follow the market's precision; quote currency 2). Sign and colour for PnL **plus** a `+`/`−` sign and an up/down icon — never colour alone.
* **Percentages:** one decimal; the API already sends percent units (`return_pct`), do not multiply again.
* **Time:** local zone with the zone shown; **UTC explicit** for bars, signals and the daily cap ([04](04-api-client.md#dates-and-time)). Relative times ("há 3 s") have the absolute time in a tooltip.
* **Identifiers** (`client_order_id`, `exchange_order_id`, hashes): monospace, truncated with a copy button.
* **Tables:** sortable columns have an accessible sort state; wide tables scroll horizontally *inside* the table container on phones, never the page (UI-7).

## 5. Copy

* UI text is Brazilian Portuguese, direct, no internal codes: say what happened and what to do. Keep one glossary and use it everywhere: *Bot*, *Estratégia*, *Backtest*, *Conexão*, *Ordem*, *Sinal*, *Posição*, *Portfólio*, *Teto de risco*, *Kill switch*, *Iniciar / Pausar / Parar*, *Promover para live*, *Aprovação*. A new term is added to `docs/ui-glossary.md` before it is used in code (aura GOLD-4).
* Domain words with no good translation (*kill switch*, *backtest*, *stop*, *take profit*, *drawdown*) stay as is, consistently.
* Backend `detail` strings are in English. They are mapped to pt-BR copy where a mapping exists; safety refusals (UX-12) are shown as received, with a pt-BR lead-in.
* Risk language: no "garantido", no implied performance. Results pages state they are historical or simulated (UX-6).

## 6. Responsive and accessible (aura UI-7, UI-8)

* Works at 360 px, tablet and desktop; no horizontal page scroll; touch targets ≥ 44 px; lost-ui's bottom bar for the main sections on phones. **Check each new screen in a real browser** — the library's own tests prove structure, not layout.
* Keyboard: every action reachable; focus visible; dialogs trap and restore focus; overlays always have a title (hidden visually if needed).
* State and meaning never by colour alone (PnL sign, mode, stale, error all have text or an icon).
* `prefers-reduced-motion` is honoured by the library; do not add `motion` code. Pulsing indicators respect it.
* Charts have a text alternative (a summary line and the underlying table one click away).
* Contrast: body text AAA (7:1) on its surfaces as in aura's palette standard; verify new colour pairs, including the `--live` token on both themes, before use.

## 7. Performance

* Polling intervals are in [04](04-api-client.md#polling-decision-f10); a hidden tab does not poll. Equity and candle series are bounded by `limit`; very long series are down-sampled **in the chart helper** (draw ≤ ~1 000 points), not by dropping data silently from tables.
* Route-level code splitting (Start's default): `lost-ui/charts` and `recharts` load only on screens that chart.
