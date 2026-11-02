# Derivatives and perpetual futures

This document records the domain boundary required to add futures without changing the meaning
of existing spot bots. **The current Binance adapter remains spot-only.** The product and order
contracts and linear-perpetual accounting primitives are now explicit, but they are not yet wired
to the bot API, persistence, worker, backtester or a Binance USD-M adapter. Futures must not be
selected for a bot until those layers are complete.

## Keep instrument, position and order action separate

- `TradingProduct` identifies spot or a linear perpetual.
- `PositionSide` identifies the exposure being held: long or short.
- `Side` on an order remains the exchange action, buy or sell. A short entry is a sell; a short
  exit is a buy with `reduce_only` enabled.
- `MarginMode` selects isolated or cross margin. Start futures support with isolated margin.
- Leverage belongs to a futures position/order configuration, never to the spot portfolio.

`MarketOrderRequest` carries these fields and validates product-specific combinations. Exchange
capabilities state which products and maximum leverage a concrete adapter actually supports. The
global domain ceiling is 10x; a venue may advertise a lower ceiling. Requests beyond either limit
must be rejected before sending them to the exchange.

## Accounting boundary

`PortfolioState` remains a spot ledger: quote cash, base quantity, and spot cost basis. Linear
perpetual accounting uses `LinearPerpetualPosition`, where quantity is a contract exposure,
initial margin is quote collateral, and PnL is marked against the entry price. Funding is recorded
as a separate cash flow. Liquidation estimates are indicative only; the venue's mark price,
maintenance tiers, fees, and liquidation engine remain authoritative.

Do not add a signed quantity to `PortfolioState` and treat it as futures support. Persist a separate
derivatives position and margin ledger, including isolated collateral, realized PnL, funding,
maintenance tier, mark price, and exchange position identifier. Reconciliation must compare that
ledger with the exchange position before a futures bot can start.

## Required implementation sequence before enabling futures

1. Add `product`, `position_side`, `margin_mode`, and `leverage` to bot configuration, API
   schemas, frontend forms, approval fingerprints, database migration, and audit records.
2. Split Binance market data/catalog access by spot and USD-M perpetual market. Perpetual symbols
   must retain quote/settlement identity (for CCXT, commonly `BTC/USDT:USDT`) and must not be
   silently normalized to spot symbols.
3. Implement a Binance USD-M adapter with isolated-margin and leverage configuration, hedge/one-way
   mode awareness, `reduceOnly`, futures stop orders, funding history, position reads, and exchange
   error translation. The adapter must set and verify leverage before opening exposure.
4. Replace the long-only strategy context with an explicit position view and directional entry
   intent. Strategies must be able to enter short, exit either direction, and never accidentally
   reverse or increase a position while closing it.
5. Add futures-specific sizing and risk checks: notional = margin × leverage, max 10x, available
   collateral, maintenance margin, liquidation distance, funding, fees, slippage, reduce-only exits,
   and loss limits based on marked equity.
6. Add a futures backtest simulator using mark/trigger prices and funding events. It must model
   liquidation and distinguish realized, unrealized, funding, and fee PnL before paper/testnet/live
   can use the product.
7. Enable in this order: deterministic unit/domain accounting, paper simulation, Binance futures
   testnet with reconciliation, then a separately approved live mode. Existing spot defaults and
   stored rows must migrate to `product=spot`, `leverage=1` without behavior changes.

## Current support

The Binance profile still advertises only spot markets; market listing filters out non-spot
markets. The existing strategy contract is long-only and `PortfolioState` is explicitly spot.
Therefore this change establishes extension contracts and validated accounting primitives, not
an operational futures trading path. No real futures order should be sent until the sequence above
is implemented and exercised on Binance Futures testnet.
