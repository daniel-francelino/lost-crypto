# 10 — Exchange abstraction and how to add an exchange

The rule: **one contract, one file per exchange, one place that chooses.** Nothing outside
`modules/exchanges/` knows which exchange it talks to; strategies, risk, the trading loop, the
backtester and the API depend on the contract and on plain value objects, never on CCXT or an
exchange name.

```mermaid
flowchart TB
    ENV[".env: ENABLED_EXCHANGES=binance"] --> CAT
    CAT["catalog.py<br/>AVAILABLE_EXCHANGES + build_exchange_registry()<br/>(the place that chooses)"] --> REG
    REG["ExchangeRegistry<br/>profile(id), require(id, tf), exchange(id)"]
    CONTRACT{{"Exchange (ABC)<br/>THE contract: fetch_candles, fetch_market_info,<br/>create_market_order, fetch_order, cancel_order, aclose"}}
    BASE["CcxtExchange<br/>shared CCXT behaviour (Template Method)"]
    BIN["binance.py<br/>BinanceExchange: PROFILE + parse_market"]
    OTHER["kraken.py, ...<br/>(your next exchange)"]
    CONTRACT --> BASE --> BIN
    BASE --> OTHER
    CAT -. registers .-> BIN
    REG --> CONTRACT
    CONSUMERS["BotTrader, BacktestExecutor,<br/>CandleImporter, services"] --> REG
```

## Design patterns used

| Pattern | Where | Why |
|---|---|---|
| **Adapter** | `binance.py`, one per exchange | Adapts each exchange's API to the single `Exchange` contract and returns the value objects the system expects (`Candle`, `MarketInfo`, `VenueOrder`) |
| **Ports and Adapters** (hexagonal) | `Exchange` ABC vs. consumers | The core depends on the contract; integrations plug in from outside |
| **Template Method** | `CcxtExchange` | Candle conversion, retries and error translation are written once; each exchange overrides only hooks like `parse_market` |
| **Registry + Factory** | `ExchangeRegistry` | Holds the enabled exchanges, exposes their static profile without building a network client, creates the integration lazily |
| **Strategy** (selection) | `catalog.py` + `ENABLED_EXCHANGES` | Which integration(s) a deployment uses is configuration, not code |
| **Interface Segregation** | `MarketDataSource`, `ExchangeGateway` | Consumers receive the narrow view they need; `Exchange` satisfies both |
| **Anti-corruption layer** | `ccxt_exchange.py` | CCXT exceptions become `ExchangeError` subclasses; no SDK type leaks |

## Files

| File | Role |
|---|---|
| `exchanges/application/exchange.py` | **The contract**: the `Exchange` ABC with every function an exchange must provide and what each must return/raise |
| `exchanges/domain/models.py` | `ExchangeProfile` = `ExchangeCapabilities` + `FeeSchedule` (static facts; callers branch on capabilities, never on the exchange name) |
| `exchanges/application/ports.py` | Order value objects and the narrow `ExchangeGateway` view |
| `exchanges/application/registry.py` | `ExchangeRegistry` |
| `exchanges/infrastructure/ccxt_exchange.py` | Shared base for CCXT exchanges (the only module importing `ccxt`) |
| `exchanges/infrastructure/binance.py` | **Everything specific to Binance**, in one file |
| `exchanges/infrastructure/catalog.py` | **The choice**: `AVAILABLE_EXCHANGES` (what exists) and `build_exchange_registry(enabled)` |
| `execution/venues/paper.py` | `PaperExchangeGateway`: simulated fills behind the same gateway port |

## Choosing the exchange

* `ENABLED_EXCHANGES` (environment, comma separated, default `binance`) decides which integrations
  a deployment activates. A name with no integration, or an empty list, fails at startup.
* Each bot, backtest and import carries an `exchange` id; requests naming a disabled exchange get
  a clear 422.
* Fees default to the exchange's profile when a bot/backtest does not set `fee_rate`.

## Adding an exchange (e.g. Kraken)

1. Copy `binance.py` to `kraken.py`. Change `PROFILE` (id, order types, native stops?, client-id
   length, testnet?, timeframes, fees) and override `parse_market` only if CCXT's generic
   `precision`/`limits` are not exact enough. If the exchange is not CCXT-based, subclass
   `Exchange` directly and implement the six methods.
2. Add one line to `AVAILABLE_EXCHANGES` in `catalog.py`.
3. Set `ENABLED_EXCHANGES=binance,kraken` where you want it active.
4. Add the class to `EXCHANGE_FACTORIES` in `tests/unit/test_exchange_abstraction.py`: the
   contract tests then verify it returns the expected value objects, raises the expected errors
   and exposes a complete profile.

If a method is missing Python refuses to instantiate the class; if `PROFILE` is missing the
registry refuses to register it. No change is needed in strategies, risk, trading, backtesting,
bots or the API.

## Real orders (Phase 4)

The contract now covers the whole account surface: `create_market_order`, `create_stop_order`,
`fetch_order`, `cancel_order`, `fetch_open_orders` and `fetch_balances`, all idempotent / safe by
the rules in the `Exchange` docstrings. `CcxtExchange` implements them for any CCXT exchange; an
instance created **without credentials** (the shared public one) raises `NotAuthenticated`, one
created for a connection (`ExchangeRegistry.authenticated(...)`, sandbox flag from the connection's
environment) can trade. The paper venue implements the order operations through the narrower
`ExchangeGateway` port. Details and safeguards: [doc 12](12-testnet-and-reconciliation.md).

## Stops: native on the exchange, engine-side as the fallback

`ExchangeCapabilities.native_stop_orders` states whether an exchange keeps stop orders itself.
Paper and backtests monitor stops candle by candle (low/high). Real-exchange bots on an exchange
with native stops rest the stop on the exchange, so it fires even when the worker is down; the bot
falls back to watching it when placement fails. See [doc 12](12-testnet-and-reconciliation.md).
