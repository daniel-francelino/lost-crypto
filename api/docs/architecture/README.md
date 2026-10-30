# Lost Crypto — Backend Architecture (`api/`)

Architectural reference for the Lost Crypto backend. **Documentation only** — no code, dependencies, FastAPI scaffolding or migrations exist yet. Scope is strictly `api/`; the frontend (`app/`) is out of scope and only interacts through the documented HTTP API.

> **Disclaimer.** No strategy is assumed to generate profit. The architecture exists to make experimentation safe, observable and reproducible, and to make real-money trading hard to trigger by accident.

## Index

| # | Document | Content |
|---|---|---|
| 01 | [Stack and technology roles](01-stack.md) | Each technology, its role, MVP vs later |
| 02 | [Architectural approach](02-architecture.md) | Modular monolith, layers, dependency rules, patterns |
| 03 | [Business modules](03-modules.md) | Boundaries, entities, interfaces, rules, MVP scope |
| 04 | [Bot architecture](04-bots.md) | Bot / Strategy / Trading Engine / Execution Engine, lifecycle, diagrams |
| 05 | [Execution environments](05-execution-environments.md) | Backtest, paper, testnet, live; live-trading safeguards |
| 06 | [Reliability and security](06-reliability-security.md) | Idempotency, reconciliation, risk, credentials, audit |
| 07 | [Background processing](07-background-processing.md) | Worker model, API ↔ engine communication, recovery |
| 08 | [Database](08-database.md) | Conceptual data model and integrity rules |
| 09 | [Directory structure](09-directory-structure.md) | Feature-based layout under `api/` |
| 10 | [Exchange abstraction](10-exchanges.md) | Registry, profiles, gateway port, how to add an exchange |

## Key decisions (summary)

1. **Modular monolith**, two deployable processes from one codebase: `api` (HTTP) and `worker` (trading loops). No microservices.
2. **Hexagonal core**: domain and application layers are pure Python; FastAPI, SQLAlchemy, CCXT and Redis live in adapters.
3. **One execution abstraction** (`ExecutionVenue` port) with four adapters: backtest, paper, testnet, live. Strategies never know which one is active.
4. **Live trading is off by default** and requires several independent, explicit opt-ins (see doc 05).
5. **PostgreSQL is the source of truth** and the command channel. The API never runs trading loops; it writes desired state (`bot.desired_state`) and the worker reconciles toward it.
6. **MVP has no Celery and no Redis**: one asyncio worker process supervised by Docker. Both are adopted only when a concrete need appears.
7. **Orders use a client-generated idempotency key persisted before submission** (write-ahead intent), which prevents duplicate orders after crashes or retries.
8. **All money/quantities are `Decimal`** in the domain and `NUMERIC` in PostgreSQL; floats are allowed only in analytics/backtest numerical kernels.

## Roadmap (suggested)

| Phase | Goal |
|---|---|
| 0 | Skeleton: config, DB, health, Docker Compose, CI (ruff, mypy, pytest) |
| 1 | Market data (Binance public REST), Strategy port, Backtesting with one simple strategy |
| 2 | Bots, paper trading, orders/fills, portfolio, analytics, audit |
| 3 | Risk management hardening, worker recovery, reconciliation |
| 4 | Binance testnet adapter |
| 5 | Live adapter behind all safeguards, tiny capital, manual approval gates |

## Conventions

- English for code, identifiers and docs. UTC everywhere. Timestamps are timezone-aware.
- Every term in this doc set is defined once; see the glossary below.

## Glossary

| Term | Meaning |
|---|---|
| Bot | Configured instance: strategy + params + capital + risk limits + execution mode |
| Strategy | Pure, reusable algorithm: market snapshot + state → signals |
| Signal | Strategy's *intent* (e.g. "buy 0.1 BTC at limit X"); not an order |
| Order intent | A signal that passed risk validation and is persisted, not yet submitted |
| Order | Intent submitted to a venue, tracked through its state machine |
| Venue | Where orders go: simulated engine, testnet, or live exchange |
| Trading session | One continuous run of a bot in a given mode |

## Implementation notes (deviations from the conceptual model)

| Phase | Simplification | Revisit when |
|---|---|---|
| 2 | `bot_portfolios` (cash + one position per bot) replaces `balances` + `positions` + `ledger_entries`; orders, fills and snapshots are the history | multi-symbol bots, shared accounts, testnet/live reconciliation |
| 2 | No separate `strategy_configs` table: the bot row holds the current config and `config_version`; sessions record the version they ran | config history must be queried or diffed |
| 2 | One supervisor loop iterates all bots sequentially (failures isolated per bot) instead of one asyncio task per bot | many bots or slow strategies |
| 2 | Paper orders are created and filled in one transaction; the INTENT→SUBMITTING→UNKNOWN states exist in the domain for testnet/live | testnet adapter (Phase 4) |
| 2 | Paper reference price is the close of the signal candle (no live ticker call) | tick-level strategies |
| 3 | Stop-loss / take-profit are monitored by the bot per closed candle (low/high), not placed as native exchange orders | Binance testnet/live gateway (Phase 4): use `native_stop_orders` |
| 3 | `ExchangeGateway` has only the paper implementation; there is no account/balances port | credentials + reconciliation (Phase 4) |
| 3 | Backtests apply stop/take-profit from the signal but still size trades all-in (no `assess_signal` sizing) | backtests must mirror bot risk sizing |
| 3 | Global risk limits come from environment variables (`RISK_MAX_*`) and use cost basis, not mark-to-market | portfolio-level risk (VaR, correlation) |
| 3 | "Cooldown after losses" is implemented as a pause after N consecutive losing round trips | time-based cooldown is needed |
