# 05 — Execution Environments

## Common abstraction

Strategy, risk and the trading pipeline are identical in every mode. Only the **ports behind the engine** change.

```python
# Illustrative contracts only
class ExecutionVenue(Protocol):
    mode: ExecutionMode

    async def submit(self, order: OrderIntent) -> VenueAck: ...
    async def cancel(self, client_order_id: str) -> None: ...
    async def fetch_order(self, client_order_id: str) -> VenueOrder | None: ...
    async def fetch_fills(self, since: datetime) -> list[VenueFill]: ...
    async def fetch_balances(self) -> list[VenueBalance]: ...


class MarketDataProvider(Protocol): ...  # historical or live


class Clock(Protocol): ...  # wall clock or simulated clock
```

A `RunProfile` bundles the adapters for a mode and is assembled by `ExecutionVenueFactory` in the composition root:

| Mode | MarketDataProvider | Clock | ExecutionVenue | Credentials | Real orders? |
|---|---|---|---|---|---|
| `backtest` | Historical (DB/Parquet) | Simulated, advanced per candle | `BacktestVenue` (fill model, fees, slippage) | None | No |
| `paper` | Live (real market data) | System | `PaperVenue` (simulated fills); USDⓈ-M uses mark candles, funding, and account tiers | None for Spot; active Binance USDⓈ-M Demo read key for Futures tiers | No |
| `testnet` | Live (testnet or mainnet data) | System | `CcxtVenue` bound to selected Demo/testnet URL | Matching Demo/testnet keys | Fake money on exchange sandbox |
| `live` | Live | System | `CcxtVenue` bound to production | Production trade-only keys | **Yes** |

### Differences that matter

| Aspect | Backtest | Paper | Demo / testnet | Live |
|---|---|---|---|---|
| Data | Historical, closed candles | Real-time | Real-time (testnet liquidity is unrealistic) | Real-time |
| Fill realism | Model: next-bar open ± slippage, fees | Model against live book/last price; latency optional | Exchange matching engine, but thin/artificial book | Real |
| Network failure modes | None | None (simulated optionally for chaos tests) | Real | Real |
| Rate limits | Not applicable | Not applicable | Real | Real |
| Speed | As fast as possible | Real time | Real time | Real time |
| Purpose | Hypothesis testing | Behaviour under live data, no exchange orders | Validate integration & order lifecycle | Real execution |

Caveat to document in UI/API: paper and backtest results **overestimate** achievable performance (no queue position, no market impact, optimistic fills). Testnet validates plumbing, not profitability.

## Replaceability without touching strategies

- Strategies receive only `StrategyContext`; they have no import of any venue, exchange or clock implementation.
- Switching a bot's mode creates a **new trading session** (and for live, a new approval); venue instances are never mutated in place.
- A **contract test suite** runs against every `ExecutionVenue` implementation (submit/cancel/fetch, partial fills, rejects, duplicate `client_order_id`, precision) so adapters are interchangeable. Paper and backtest venues are the reference implementations of the same semantics (idempotent by client id, same rejection reasons for min-notional and precision).
- Exchange constraints (tick size, lot size, min notional) are enforced by the same `OrderNormalizer` in every mode, so a paper order that would be rejected live is rejected in paper.

## Live trading: disabled by default

> **Implemented.** Each safeguard below, with where it is enforced and what was and was not
> verified, is in [doc 13](13-live-trading.md).

Live trading requires **all** of the following (defense in depth; any one missing → refuse):

1. **Global flag** `LIVE_TRADING_ENABLED=true` in the worker's environment (default `false`; absent from `.env.example` defaults; separate from the API's env).
2. **Separate live exchange connection** with `environment=live` and production credentials; testnet/paper connections can never be used with live URLs (adapter is bound to one environment at construction; base-URL assertion in the adapter).
3. **Bot-level opt-in**: `mode=live` set explicitly; default is `paper`. Changing to live is a dedicated endpoint, not a generic PATCH.
4. **Explicit confirmation** step: a short-lived, single-use confirmation token (and a typed confirmation phrase in the UI such as the bot name) bound to bot id + config version. Any config change invalidates it.
5. **Prerequisite history**: configurable gate such as "bot completed ≥ N days of paper trading without risk breaches" (advisory in MVP, enforced later).
6. **Hard caps independent of bot config**: global `MAX_LIVE_NOTIONAL_PER_ORDER`, `MAX_LIVE_TOTAL_EXPOSURE`, and `MAX_LIVE_DAILY_LOSS` read from environment (not editable via API) to bound blast radius.
7. **Credentials**: trade-only permission, withdrawals disabled, IP whitelisted; the system verifies permissions on connect and refuses keys with withdrawal rights.
8. **Kill switch** (global and per bot) always available; trips automatically on daily-loss breach, repeated errors, reconciliation mismatch.
9. **Startup guard**: on worker boot, log a prominent banner of active modes; if live bots exist and the flag is off, they are put in `error`/`paused` instead of being downgraded silently.
10. **Audit**: every live activation, config change, order and kill-switch event is written to `audit_events`.

### Environment separation

| Concern | Separation |
|---|---|
| Config | Distinct env files / secrets per environment; `APP_ENV` in (`local`, `test`, `prod`) |
| Database | Separate databases (never share a DB between local/paper experiments and live) — recommended: separate Postgres instance for live when it starts |
| Credentials | Different vault keys; testnet keys can't be stored in a `live` connection and vice versa (validated by environment tag and a probing call) |
| Tests | CI never has live credentials; live adapter code paths are unreachable without the flag, and unit tests assert it |
| Docker Compose | Local compose never defines live keys or `LIVE_TRADING_ENABLED` |
