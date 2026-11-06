# Futures delivery plan

## Outcome

Make Binance USD-M USDT perpetuals operational end to end while preserving existing spot bots.
The first supported release is deliberately narrow:

- Binance USD-M perpetuals settled in USDT (for example CCXT `BTC/USDT:USDT`).
- One-way position mode, one directional position per bot: long **or** short.
- Isolated margin only; leverage configurable from 1x through 10x, default 1x.
- Paper simulation first, then Binance Futures Demo; live remains behind existing approval and
  risk safeguards and is enabled only after Demo sign-off.
- Existing spot bots, API payloads, portfolio accounting, and defaults remain spot with 1x.

Cross margin, hedge mode (simultaneous long and short for one symbol), COIN-M contracts, options,
multi-exchange futures, and portfolio-margin accounts are out of the first release. They require
different collateral and position semantics. Isolated margin is the initial choice so a loss on
one position does not draw on the shared account collateral as cross margin can.

## Current implementation status

The repository has moved beyond the original spot-only baseline. It now has separate Binance Spot
and USDⓈ-M adapters, `demo` as a persisted connection environment, Demo REST host validation,
product/leverage/margin fields in bot configuration, a Futures-specific ledger, a paper worker for
long and short positions, and an initial USD-M bot workflow. These are implementation components,
not evidence that the release gates below have passed.

| Phase | Current state | Remaining before its gate passes |
|---|---|---|
| 0–1 | Product constraints and bot persistence/configuration are implemented. Deterministic API schema tests prove that bot/backtest endpoints accept 10x, reject 10.01x and 11x, and preserve legacy Spot/1x/long-only defaults. Unit mapping tests round-trip Spot and Futures configurations and confirm Futures risk fields appear in config diffs (which bump the approval version). The public API schema exposes isolated margin only, rejects cross margin for bots/backtests, and the generated frontend enum matches OpenAPI. The update service preserves the Demo connection when a Futures bot changes to paper, keeps Spot paper accountless, and refuses edits/product switches while either ledger has exposure, reservations, or unresolved orders. The PostgreSQL integration test now PATCHes an approved bot, reads back the persisted config/approval columns, verifies the pending token is bound to the prior version, and confirms the old token cannot start the bot. An isolated PostgreSQL schema completed the full upgrade to 0039, Spot/Futures create and read, Futures update/read, defaulted legacy Spot read, and downgrade to 0035. The 0036 downgrade emits a database-side duplicate-owner guard before restoring the stricter unique index. Futures account/symbol uniqueness applies to active bots; the locked start check also considers open exposure and unresolved orders. | Run the full PostgreSQL integration suite at the current migration head; keep the user's shared database migration state separate from verification databases. |
| 2 | USD-M market catalog, market rules, mark prices/candles, funding reads, and leverage tiers exist. Market-rule lookup rejects spot, inactive, inverse, non-USDT-settled, and mismatched symbols before their rules can be used. Persistence primary keys include exchange identity for trade and mark candles; repository and frontend query-key tests now guard isolation between Binance Spot and USD-M for BTC/USDT. | Prove runtime data freshness under an active exchange connection; auxiliary historical completeness remains explicitly uncertified. |
| 3 | Futures ledger, isolated margin model, fees, funding, maintenance tiers, and liquidation simulation exist. Funding now debits unreserved wallet balance before isolated margin, credits receipts to wallet balance, preserves pending-order reservations, and caps settlement at available wallet plus isolated collateral. Entry leverage is checked before division and against the opening notional bracket; paper marking retains higher maintenance brackets if notional grows after entry. The exchange executor replaces a native stop when a partial fill changes position size, uses a fresh client order ID, and pauses the bot if Binance does not confirm cancellation of the stale stop. Deterministic tests cover maintenance-bracket boundary selection, partial entry fill deduplication and margin reservation/release, cumulative partial reduce-only fills and realized PnL, stop replacement after a partial close, fail-closed behavior on cancel uncertainty, funding cash-flow paths, collateral accounting, and the 10x domain cap. | Run full database integration at the current migration head and verify exact settlement parity against Binance Demo account events. |
| 4 | The paper Futures path supports directional long/short accounting. Futures sessions pin leverage-tier inputs, and parity replay uses stored signal, mark, and funding series with the isolated-perpetual simulator. Replay refuses sessions whose bot configuration changed afterward. Signal-close replay evaluates warmup candles to initialize strategy state while suppressing warmup fills, matching paper startup semantics. Golden tests execute the actual paper worker and replay for mirrored long/short mean-reversion and trend-breakout sessions and assert identical signals, fills, and final equity. Intrabar mark exits use the candle close as their observable timestamp because OHLC data cannot identify the exact trigger time. Strategy tests also cover mirrored short breakout levels, same-candle reversal rejection, and mean-reversion short exits when new shorts are disabled. | Golden worker/replay parity now covers both enabled Futures strategies in both directions; retain Spot sequence regression coverage and extend golden coverage when strategies are added. |
| 5 | Futures backtests are wired through separate signal/mark candles, event-time funding (including same-time Regular and Special events), pinned leverage tiers, fees, liquidation, data hashes, cost sensitivity, and distinct funding/liquidation outputs, including minimum intrabar liquidation distance. The run refuses missing or misaligned mark candles, funding events without event-time mark prices, empty funding history on ranges of at least eight hours, and observed funding gaps longer than eight hours. Results expose funding coverage as `not_certified` because historical interval schedules are not stored. Deterministic coverage checks long/short PnL and funding direction, adverse gap liquidation fills, maintenance-tier changes when mark notional crosses a bracket, mirrored long/short stop, target, and stop-gap exits, missing-data rejections, repeatability, partial closes that retain protective stops, and cost-ladder parity with a full Futures run; Spot backtest regression cases pass alongside them. | Deterministic tests cover hourly funding settlements, event-time accounting, an observable missing hourly observation, and inclusive import of a settlement at the requested end boundary. Partial closes, full-run reproducibility, and the Futures cost-ladder base path also have deterministic unit coverage. Historical funding completeness remains uncertified because Binance does not provide the historical interval schedule alongside each rate row. |
| 6 | USD-M REST adapter, account reads, position normalization, start-time market configuration, available-USDT check, protective Algo Order mapping (including a request-level regression against the locked CCXT version), REST reconciliation, Demo private-stream monitor, and explicit kill-switch close policy exist. `BotTrader` routes futures PAPER and TESTNET to separate `PerpetualPaperTrader` and `PerpetualDemoTrader` classes. Demo commits entry/reduce-only intents and margin reservations before calling `OrderExecutor`; only exchange fills mutate positions. Before a Demo entry intent is persisted, the signal must contain a protective stop and its stop/target geometry is validated against the directional position. Paper funding estimates are not applied in Demo. Funding `ACCOUNT_UPDATE` events resolve to signed REST `FUNDING_FEE` income and update the ledger once by transaction ID using the exchange-reported isolated wallet; reconciliation detects isolated-margin drift. Unit tests cover Demo entry/close intent behavior, actual funding cash-flow accounting, duplicate event delivery, restart backfill idempotency, fail-closed recovery when isolated-margin drift is unexplained or funding predates a later local position change, and full-page funding pagination with overlap deduplication and backwards-cursor rejection. An ambiguous Futures order outcome retains its margin reservation and cannot be submitted again before resolution; a deterministic executor test covers this unknown state. A defensive `OrderExecutor` gate rejects and audits any residual Futures LIVE order before exchange resolution while releasing its collateral reservation. Funding recovery pages the Binance income history for up to 89 days after a stream gap or restart. It applies missing entries only when the local position has not changed since those funding events and the current exchange position and isolated margin are explainable; ambiguous histories fail closed. Futures reconciliation reads all non-zero USD-M positions for the account whenever it has Futures bots, including symbols not assigned to a bot, so unowned/manual exposure becomes a mismatch and pauses the connection's bots. An account-wide open-order scan at startup/recovery and every 60 seconds flags unknown standard or Algo orders on unassigned contracts; assigned contracts remain checked on the regular reconciliation pass. A unit test covers an unowned ETH position and an unowned manual open order alongside a BTC bot. Futures kill-switch success is audited only after Binance Demo reports no open position or orders and the local ledger has no position or unresolved orders; tests cover stale exposure, including remote exposure absent from the local ledger. The kill switch checks Demo even when the local ledger is flat and fails closed on orphan exposure. Every Demo start/resume resolves connection-scoped pending orders, requires a clean account-wide reconciliation, and validates aggregate capital reserved by bots not fully stopped against total USDT. Connection-scoped queries avoid the global bot-list limit. The USD-M adapter refuses the live-host SAPI permission endpoint in Demo/Testnet. A session start does not alter leverage or margin while an existing owned position is open. An explicitly opted-in smoke test now covers capped long and short Demo entries, private order events, native stops, reduce-only closes, and residual cleanup. No Binance Demo runtime evidence exists. | Run the opt-in smoke test and test partial/unknown fills, stop arming/replacement, restart recovery and kill behavior end to end; verify every exchange position against its ledger in Binance Demo. Keep the worker opt-in required and live blocked until the gate passes. |
| 7 | Initial product selection, Futures risk fields, and bot detail/accounting views exist. The Futures backtest form selects the USD-M Demo account for leverage tiers, imports mark/funding data, and displays funding-coverage quality. Opening a backtest from a bot now preserves product, symbol, leverage, short mode, account, capital, fees, slippage, parameters, and risk. Existing Futures Demo bot edits display the persisted Demo mode and explain that exchange orders are sent; creating a new Futures bot remains paper-only pending the Demo release gate. System status reports Futures Demo positions without a confirmed active native stop. Deduplicated worker alerts cover exposed positions, stale mark prices (15-second freshness limit), narrow liquidation distance (configured minimum or 10%, critical below half), stream/margin/reconciliation recovery pauses, and net funding paid above 1% (warning) or 2% (critical) of allocated capital, offset by funding received. Liquidation alert payloads identify whether the price is Binance-reported or locally estimated; the alerts table exposes bot ID and diagnostic payload, and the audit table supports expanded event payloads. OpenAPI and frontend types include the position product and alert kinds so the UI distinguishes Spot from USD-M. Local verification: frontend typecheck/lint, 147 unit tests, and production build pass; the available login accessibility/shell E2E checks pass (3 passed), while 14 authenticated/backend-dependent E2E cases, including the 360 px review and logged-in accessibility scans, were skipped because E2E users/API were unavailable. | Responsive/accessibility review on authenticated screens and end-to-end consistency across bot configuration, backtests, dashboard, alerts, and audit remain incomplete. |
| 8 | Futures paper is locally opt-in; Binance Demo endpoints are configured per connection. | Complete phases 5–7 and the phase 6 fault/recovery gates before enabling automated Futures Demo orders. Live remains disabled. |

Do not describe USDⓈ-M exchange execution as operational until its phase 6 gate passes in Binance
Demo and every release gate below has auditable evidence. Paper results are simulated results and
do not establish exchange execution parity.

## Delivery phases and gates

### 0. Lock product and safety decisions

- Confirm Binance USD-M, USDT settlement, isolated margin, one-way mode, 1x default, 10x hard cap.
- Define instrument identity separately from display ticker; a perpetual must not be confused with
  its spot pair.
- Define the per-account collision invariant: until an account-level futures ledger exists, only
  one active futures bot may own a given exchange connection + perpetual symbol.
- Keep cross margin and hedge mode unavailable in the UI and reject them in the API for v1.

**Gate:** product rules are represented in a short ADR and enforced by domain validation; legacy
spot create/update payloads still produce spot/1x configurations.

### 1. Generalize configuration, API, and persistence

- Add `product`, `leverage`, and `margin_mode` to bot and backtest configuration, API schemas,
  response validation, audit diffs, live approval fingerprints, and frontend API types.
- Store these fields in bot/backtest rows with a migration defaulting all existing records to
  `spot`, leverage `1`, and no futures margin mode.
- Extend exchange capabilities by product and max supported leverage. Reject unsupported
  product/leverage combinations in application validation before calling an adapter.
- Keep order action (`BUY`/`SELL`) distinct from position intent (`LONG`/`SHORT`) and close intent
  (`reduce-only`). Translate to the exchange's selected position mode only inside its adapter.

**Gate:** migration upgrade/downgrade is safe; API serialization round-trips old spot records;
10x is the maximum accepted futures leverage at every entry point; 10.01x and 11x are rejected.

### 2. Add Binance USDⓈ-M market data and instrument catalog

- Introduce a separate market-data source/profile for USDⓈ-M; do not switch the existing spot
  client's default market type globally.
- Load contract metadata, active status, settlement asset, lot size, tick size, minimum notional,
  contract size, and leverage tiers from the futures market catalog.
- Accept and persist a canonical linear symbol (CCXT commonly uses `BTC/USDT:USDT`); show users
  `BTCUSDT Perp` or equivalent while retaining the settlement asset in details.
- Fetch regular OHLCV for signals and mark-price candles/stream for unrealized PnL, stop triggers,
  and liquidation calculations. Record which price source each value uses.
- Fetch funding history/rates and timestamp them; never infer historical funding from the current
  rate.

**Gate:** spot and futures symbols with the same base/quote can coexist without cache, query-key,
or persistence collisions; inactive and unsupported contracts cannot be selected.

### 3. Build derivatives ledger and risk model

- Create futures-specific position, collateral, and funding records instead of overloading the
  spot `bot_portfolios` cash/quantity ledger.
- Track signed exposure, entry/mark price, isolated margin, leverage, realized/unrealized PnL,
  fees, funding, maintenance-margin tier, liquidation price, exchange position identifier, and
  reconciliation timestamp.
- Size a position from user risk and available collateral. Enforce notional/collateral checks,
  venue leverage tiers, 10x system cap, max order notional, daily loss/drawdown limits, and a
  configurable minimum liquidation-distance buffer.
- Reserve collateral for pending orders before submission and release it on rejection/cancel.
- Calculate marked equity and risk from mark price. Include taker fees, slippage, funding, and
  liquidation/close-out fees. A liquidation estimate is a warning; exchange-reported liquidation
  state/price is authoritative.
- Define handling for gaps through a stop, partial fill, funding timestamp, and exchange
  liquidation. Preserve immutable ledger entries for every balance change.

**Gate:** deterministic accounting covers long and short PnL, fee and funding cash flows, margin
reservation, partial closes, stop exits, and liquidation; no path can increase exposure when
closing a position.

### 4. Add directional strategy semantics and parity

- Replace the implicit long-only `position_quantity` strategy view with an explicit position view
  (`flat | long | short`, quantity, entry price) and directional entry/exit intents.
- Update mean-reversion and breakout strategies to have documented long-only or long/short modes.
  Long-only behavior remains the default for existing bots. Short signals and protective stop /
  take-profit levels must be mirrored correctly.
- Ensure the worker, risk engine, paper executor, persisted signals/orders, and parity replay all
  consume the same intent model.
- Prevent an exit from accidentally opening a reverse position. A reversal must be two explicit,
  risk-checked actions: reduce/close, then open the opposite side.

**Gate:** a golden signal/fill replay produces identical decisions in worker and parity replay for
both long and short sessions; legacy spot signal sequences stay unchanged.

### 5. Upgrade backtests before futures paper/live

- Add product, leverage, margin mode, position direction, and funding dataset/version to each run's
  immutable configuration.
- Simulate collateral reservation, mark-to-market equity, funding events, maintenance margin,
  liquidation, fees, slippage, and partial exits.
- Keep signal-price candles separate from mark-price series. If required mark/funding history is
  missing, refuse the run or mark it incomplete; never silently substitute spot close prices.
- Report spot and futures metrics distinctly, including maximum leverage, maximum notional,
  liquidation count/time, funding paid/received, and liquidation distance.
- Re-run the existing robustness, out-of-sample, significance, and cost-sensitivity reports with
  futures accounting semantics.

**Gate:** deterministic fixtures cover long and short profits/losses, funding paid/received,
liquidation between candles, stop gaps, and missing auxiliary data; same strategy/config yields
repeatable results.

### 6. Implement the Binance USDⓈ-M execution adapter

- Use a separate authenticated USDⓈ-M client and environment configuration for production and
  Binance Demo; spot credentials/endpoints must not be reused implicitly.
- Wire Futures Demo bots to an exchange execution path distinct from `PerpetualPaperTrader`; a
  Demo bot must never book a simulated paper fill as an exchange execution.
- At start, verify account futures permission, one-way position mode, margin mode, and existing
  position/order state. Configure isolated margin and requested leverage for the exact symbol;
  read them back and block start if they differ or exceed 10x/venue tier limits.
- Map order direction, position side, reduce-only, client order id, stops, and fills according to
  Binance's current one-way semantics. Keep all writes idempotent and resolve unknown outcomes by
  client order id before retrying.
- Add futures position/account reads and user-data stream support for order updates, account
  configuration, margin calls, and disconnect/reconnect. REST reconciliation remains the recovery
  authority after a stream gap.
- Add a global kill path that cancels opening orders and closes positions only under an explicit,
  audited policy; a kill switch must never silently leave an unprotected position.

**Gate:** contract tests and Binance USDⓈ-M Demo prove start/configuration, long/short open and
reduce-only close, protective stop, restart reconciliation, duplicate/unknown outcomes, stream
reconnect, and kill-switch behavior. Every scenario verifies exchange position against the local
ledger.

### 7. Add frontend workflow and operational visibility

- Add Spot / USDⓈ-M Perp product selection. Show supported contract symbols only after product
  selection and label settlement currency clearly.
- Show leverage as an integer input/select from 1x to 10x, default 1x, with estimated collateral
  and notional. Do not imply that 10x is recommended.
- Show position direction (strategy mode), isolated margin, estimated liquidation price/distance,
  mark price, unrealized PnL, funding, and margin usage in dashboard and bot detail.
- Add explicit risk confirmation in bot configuration and a futures-specific live approval summary
  including symbol, direction mode, leverage, margin, and max notional.
- Add alerts for margin buffer, stale mark price, funding, liquidation, exchange/local mismatch,
  and stream disconnect. Distinguish estimated from exchange-reported liquidation values.

**Gate:** all futures fields appear consistently in create/edit/detail, orders, backtest, dashboard,
audit, and alerts; accessibility and responsive layouts are verified.

### 8. Staged release

1. Run migrations and all API/frontend checks in CI; retain existing spot regression coverage.
2. Enable paper futures behind `FUTURES_PAPER_ENABLED` and reconcile paper ledger invariants.
3. Enable Binance Demo execution for an allowlisted account and symbols. Require operator review
   of each Demo result and perform fault-injection/restart checks.
4. Ship read-only live account/position monitoring first.
5. Enable live futures only behind a separate capability and approval, with a 1x default, hard 10x
   cap, small notional cap, one symbol/account collision guard, and tested emergency procedures.
6. Expand symbols and account concurrency only after operating evidence; cross margin and hedge mode
   require a separate design/review.

**Release gate:** no unresolved ledger mismatch, unhandled liquidation/partial-fill case, missing
funding history path, or unknown order outcome is accepted. Live remains disabled if any gate fails.

## Suggested implementation order

Phases 0–3 form the backend foundation. Phase 4 enables short-capable strategy semantics. Phase 5
is a hard dependency for meaningful paper and Demo comparisons. Phase 6 then connects exchange
execution; phase 7 adds the user workflow. Release phase 8 only begins after all gates pass.

## Current code to reuse or replace

- Reuse the recently added `TradingProduct`, `PositionSide`, `MarginMode`, capability limits,
  `MarketOrderRequest` validation, and `LinearPerpetualPosition` as starting points.
- Keep `PortfolioState` and existing spot exchange implementation explicitly spot-only.
- Refactor `StrategyContext.position_quantity`; do not reinterpret the existing positive spot
  quantity as a signed futures position without updating every strategy and replay consumer.
- Add new migrations rather than changing prior migration history.

## Primary references

- [Project USD-M v1 decisions](17-usdm-v1-adr.md)
- [Project Binance Demo integration guide](18-binance-demo-integration.md)
- [Binance Developer Docs: USD-M Futures](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/Introduction)
- [Binance Developer Docs: New USD-M Order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order)
- [Binance Developer Docs: USD-M user data stream order updates](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams#event-order-update)
- [Binance Developer Docs: Mark Price Klines](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data)
- [Binance Developer Docs: Change Initial Leverage](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Initial-Leverage)
- [CCXT Manual: contract markets, leverage, margin mode, and position mode](https://github.com/ccxt/ccxt/wiki/Manual)
