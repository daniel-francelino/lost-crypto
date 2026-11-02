# Futures delivery plan

## Outcome

Make Binance USD-M USDT perpetuals operational end to end while preserving existing spot bots.
The first supported release is deliberately narrow:

- Binance USD-M perpetuals settled in USDT (for example CCXT `BTC/USDT:USDT`).
- One-way position mode, one directional position per bot: long **or** short.
- Isolated margin only; leverage configurable from 1x through 10x, default 1x.
- Paper simulation first, then Binance Futures testnet; live remains behind existing approval and
  risk safeguards and is enabled only after testnet sign-off.
- Existing spot bots, API payloads, portfolio accounting, and defaults remain spot with 1x.

Cross margin, hedge mode (simultaneous long and short for one symbol), COIN-M contracts, options,
multi-exchange futures, and portfolio-margin accounts are out of the first release. They require
different collateral and position semantics. Isolated margin is the initial choice so a loss on
one position does not draw on the shared account collateral as cross margin can.

## Current baseline

The exchange profile and market catalog are spot-only; strategy context and portfolio accounting
are long-only spot; orders contain only buy/sell and quantity; backtests have no collateral,
funding, or liquidation model. A preliminary product/position/leverage contract and pure linear
perpetual accounting primitives are present in the code, but they are not connected to bot config,
the worker, storage, backtests, or a futures adapter. They must not be presented as futures support.

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
  testnet; spot credentials/endpoints must not be reused implicitly.
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

**Gate:** contract tests and Binance USDⓈ-M testnet prove start/configuration, long/short open and
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
2. Enable paper futures behind a feature flag and reconcile paper ledger invariants.
3. Enable testnet for an allowlisted account and symbols. Require operator review of each testnet
   result and perform fault-injection/restart checks.
4. Ship read-only live account/position monitoring first.
5. Enable live futures only behind a separate capability and approval, with a 1x default, hard 10x
   cap, small notional cap, one symbol/account collision guard, and tested emergency procedures.
6. Expand symbols and account concurrency only after operating evidence; cross margin and hedge mode
   require a separate design/review.

**Release gate:** no unresolved ledger mismatch, unhandled liquidation/partial-fill case, missing
funding history path, or unknown order outcome is accepted. Live remains disabled if any gate fails.

## Suggested implementation order

Phases 0–3 form the backend foundation. Phase 4 enables short-capable strategy semantics. Phase 5
is a hard dependency for meaningful paper and testnet comparisons. Phase 6 then connects exchange
execution; phase 7 adds the user workflow. Release phase 8 only begins after all gates pass.

## Current code to reuse or replace

- Reuse the recently added `TradingProduct`, `PositionSide`, `MarginMode`, capability limits,
  `MarketOrderRequest` validation, and `LinearPerpetualPosition` as starting points.
- Keep `PortfolioState` and existing spot exchange implementation explicitly spot-only.
- Refactor `StrategyContext.position_quantity`; do not reinterpret the existing positive spot
  quantity as a signed futures position without updating every strategy and replay consumer.
- Add new migrations rather than changing prior migration history.

## Primary references

- [Binance Developer Docs: USD-M Futures](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/Introduction)
- [Binance Developer Docs: New USD-M Order](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Order)
- [Binance Developer Docs: USD-M user data stream order updates](https://developers.binance.com/en/docs/products/derivatives-trading-usds-futures/user-data-streams#event-order-update)
- [Binance Developer Docs: Mark Price Klines](https://developers.binance.com/docs/derivatives/usds-margined-futures/market-data/rest-api/Mark-Price-Kline-Candlestick-Data)
- [Binance Developer Docs: Change Initial Leverage](https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Change-Initial-Leverage)
- [CCXT Manual: contract markets, leverage, margin mode, and position mode](https://github.com/ccxt/ccxt/wiki/Manual)
