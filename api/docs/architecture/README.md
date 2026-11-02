# Lost Crypto — Backend Architecture (`api/`)

Architectural reference for the Lost Crypto backend. The documents describe the current implementation and planned release gates. Scope is the backend (`api/`); the frontend (`app/`) consumes the documented HTTP API.

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
| 11 | [Strategies](11-strategies.md) | One contract, one file per strategy, catalog, how to add one |
| 12 | [Testnet and reconciliation](12-testnet-and-reconciliation.md) | Credentials, two-phase orders, reconciliation, native stops |
| 13 | [Live trading](13-live-trading.md) | Real-money safeguards and the path to the first live order |
| 14 | [Authentication](14-authentication.md) | Login, sessions, roles: what the frontend uses |
| 15 | [Derivatives and perpetual futures](15-derivatives.md) | Product and position boundaries, leverage ceiling, and futures rollout requirements |
| 16 | [Futures delivery plan](16-futures-delivery-plan.md) | Phased implementation plan and release gates for operational Binance USDⓈ-M futures |
| 17 | [Binance USD-M perpetual v1 decision](17-usdm-v1-adr.md) | Product identity, account invariants, margin mode and release constraints |
| 18 | [Binance Demo integration](18-binance-demo-integration.md) | Demo credentials, Spot and USDⓈ-M endpoints, setup, safeguards, and troubleshooting |

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
| 3→4 | Paper/backtest monitor stops per candle; real-exchange bots rest a native STOP_LOSS on the exchange (take-profit is still watched by the bot) | native OCO / take-profit orders |
| 4 | Done: real order methods, account port (`fetch_balances`, `fetch_open_orders`), credentials vault, reconciliation (supersedes the Phase 3 note) | — |
| 3 | Backtests apply stop/take-profit from the signal but still size trades all-in (no `assess_signal` sizing) | backtests must mirror bot risk sizing |
| 3 | Global risk limits come from environment variables (`RISK_MAX_*`) and use cost basis, not mark-to-market | portfolio-level risk (VaR, correlation) |
| 3 | "Cooldown after losses" is implemented as a pause after N consecutive losing round trips | time-based cooldown is needed |
| 4 | Market orders only, fills found by polling (no user-data WebSocket); fee assets other than base/quote are rejected | limit orders, lower latency, BNB-discount accounts |
| 5 | Done: live connections and bots exist behind the doc 05 safeguards (see doc 13); the order path is shared with the testnet and has only been exercised against a simulated account | the first supervised run with real, tiny money |
| 4 | `bot_portfolios` reservation fields replace a separate ledger; the account check asserts "exchange holds at least what bots own" (virtual sub-accounts over one account) | per-bot sub-accounts or a ledger for exact attribution |
| 4 | Backtests still ignore the bot's risk sizing and real fee assets | align the backtester with the real-exchange pipeline |
| 5 | Live hard caps are per bot / per order / total exposure in quote currency; the daily-loss cap is per bot, not portfolio-wide | portfolio-level loss accounting |
| 5 | The paper-history gate counts snapshots of the bot's own paper sessions, and risk breach/error events before promotion | longer-horizon or out-of-sample gates |
| 5 | Auth: single-node, no MFA / password reset by email; access tokens cannot be revoked before they expire (15 min) | public deployment, multiple operators |
