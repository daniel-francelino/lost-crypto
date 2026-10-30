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
