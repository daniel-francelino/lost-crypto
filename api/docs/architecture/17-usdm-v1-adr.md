# ADR 17: Binance USD-M USDT perpetual v1

**Status:** accepted for implementation; trading remains disabled until the delivery gates pass.

## Decision

- The first derivatives product is Binance USD-M linear perpetual settled in USDT.
- Persist the CCXT unified instrument (`BASE/USDT:USDT`) as its identity. The spot instrument
  (`BASE/USDT`) is a different market, even when its display ticker is similar.
- V1 uses one-way position mode and one directional position per bot. A strategy can be long-only
  or long/short; a reversal must close the existing exposure before it opens the other direction.
- Isolated margin is mandatory. Leverage is an integer from 1x to 10x, defaults to 1x, and is
  checked against the exchange's instrument tier before any order.
- USD-M Single-Asset Mode is required so collateral and the v1 futures ledger remain USDT-valued;
  Multi-Assets Mode, cross margin, hedge mode, COIN-M, options and portfolio margin are excluded.
- Until account-level collision protection and reconciliation are in place, an exchange
  connection plus perpetual symbol can be owned by at most one active bot.
- Paper accounting must use a futures ledger. Testnet credentials/endpoints are separate from
  spot. Live futures remains unavailable until testnet sign-off and a separate live capability and
  approval flow exist.

## Consequences

Spot remains the default product and keeps its existing 1x, long-only configuration and ledger.
The USD-M adapter is a separate exchange integration; it must not change Binance Spot's market
type or endpoints. Product and settlement are part of every market-data and cache key.

The application rejects futures creation/backtests while their corresponding execution and
accounting paths are incomplete. This prevents a perpetual configuration from falling through to
spot sizing or spot PnL.

## Release gates

Follow [16-futures-delivery-plan.md](16-futures-delivery-plan.md) phases 1–8. No environment flag
may bypass a failed accounting, reconciliation, testnet or risk gate. Live remains disabled until
all listed prerequisites have evidence and operator sign-off.
