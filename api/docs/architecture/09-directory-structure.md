# 09 — Backend Directory Structure

> Note: the original brief was cut off in the middle of this section after `backtesting/`. The remainder below completes the tree consistently with the rest of the architecture. Proposed only — nothing is created yet.

Feature-based modules under `api/src/lost_crypto/`, with layers inside the modules that need them (see doc 02 for which). A `src/` layout with a package name avoids import ambiguity and keeps `uv`/packaging simple.

```text
api/
├── pyproject.toml                  # uv-managed; ruff, mypy, pytest config
├── uv.lock
├── Dockerfile                      # one image; api and worker differ by command
├── docker-compose.yml              # postgres, api, worker (redis later)
├── .env.example                    # no secrets; LIVE_TRADING_ENABLED absent/false
├── alembic.ini
├── migrations/                     # Alembic (created at implementation time)
├── docs/
│   └── architecture/               # this documentation
├── src/
│   └── lost_crypto/
│       ├── main.py                 # FastAPI app factory (api process)
│       ├── worker.py               # worker entrypoint (trading process)
│       ├── core/                   # cross-cutting, no business rules
│       │   ├── config.py           # pydantic-settings
│       │   ├── container.py        # composition root / DI wiring
│       │   ├── clock.py            # Clock port + system impl
│       │   ├── ids.py              # IdGenerator
│       │   ├── logging.py
│       │   ├── errors.py           # base domain/app errors
│       │   ├── money.py            # Decimal helpers, Money/Quantity VOs
│       │   ├── db/                 # engine, session, UnitOfWork base
│       │   ├── security/           # auth, CredentialVault (encryption)
│       │   └── events.py           # in-process event bus
│       ├── modules/
│       │   ├── bots/
│       │   │   ├── domain/         # Bot, BotConfig, state machine
│       │   │   ├── application/    # use cases, ports (BotRepository)
│       │   │   ├── infrastructure/ # SQLAlchemy repo + ORM models
│       │   │   └── presentation/   # router.py, schemas.py
│       │   ├── strategies/
│       │   │   ├── domain/         # Strategy Protocol, Signal, context
│       │   │   ├── catalog/        # grid.py, mean_reversion.py, trend.py ...
│       │   │   ├── registry.py
│       │   │   └── presentation/   # list strategies + param schemas
│       │   ├── trading/            # engine, sessions, supervisor
│       │   │   ├── domain/
│       │   │   ├── application/    # tick pipeline, recovery
│       │   │   ├── infrastructure/
│       │   │   └── presentation/
│       │   ├── execution/          # orders, fills, reconciliation
│       │   │   ├── domain/         # Order, state machine, OrderNormalizer
│       │   │   ├── application/    # submit, cancel, reconcile
│       │   │   ├── venues/         # backtest.py, paper.py, ccxt_venue.py
│       │   │   ├── infrastructure/
│       │   │   └── presentation/
│       │   ├── exchanges/
│       │   │   ├── application/    # ExchangePort, errors
│       │   │   ├── infrastructure/ # ccxt_adapter.py (only CCXT import), rate_limiter.py
│       │   │   └── presentation/   # connections endpoints (write-only secrets)
│       │   ├── market_data/
│       │   │   ├── domain/         # Candle, Ticker, MarketInfo
│       │   │   ├── application/    # providers, importer, gap detection
│       │   │   ├── infrastructure/ # candle repo, exchange-backed source
│       │   │   └── presentation/
│       │   ├── risk_management/
│       │   │   ├── domain/         # rules, sizers, RiskDecision
│       │   │   ├── application/    # RiskEngine, kill switch
│       │   │   ├── infrastructure/
│       │   │   └── presentation/
│       │   ├── portfolio/
│       │   │   ├── domain/         # Balance, Position, ledger
│       │   │   ├── application/
│       │   │   ├── infrastructure/
│       │   │   └── presentation/
│       │   ├── backtesting/
│       │   │   ├── domain/
│       │   │   ├── application/    # run loop using trading pipeline
│       │   │   ├── infrastructure/
│       │   │   └── presentation/
│       │   ├── analytics/
│       │   │   ├── metrics/        # pure functions (NumPy/Pandas)
│       │   │   ├── application/    # query services
│       │   │   └── presentation/
│       │   ├── audit/              # flat: model, writer, query, router
│       │   └── health/             # flat: liveness, readiness, worker heartbeat
│       └── api_router.py           # mounts every module router under /api/v1
└── tests/
    ├── unit/                       # mirrors modules/; no I/O
    ├── integration/                # Postgres container, adapters
    ├── contract/                   # ExecutionVenue / ExchangePort contract suites
    ├── e2e/                        # API + worker with paper venue
    ├── fixtures/                   # recorded exchange payloads, golden candles
    └── conftest.py
```

## Conventions

- **Imports:** a module may import another module's `application` ports or its `domain` value objects, never its `infrastructure`. Enforce with import-linter contracts or an architecture test.
- **ORM models** live in each module's `infrastructure/` and are registered with a shared `Base` in `core/db`, so Alembic sees them without cross-module coupling.
- **Only `exchanges/infrastructure` imports `ccxt`.** Only `*/infrastructure` imports `sqlalchemy`. Only `*/presentation` and `main.py` import `fastapi`. Domain packages import none of these (architecture test).
- **Two entrypoints, one codebase:** `uvicorn lost_crypto.main:app` and `python -m lost_crypto.worker`. Both use `core/container.py`; the worker's container wires venues and the vault's decrypt capability, the API's does not.
- **API versioning:** `/api/v1/...`; OpenAPI is the contract consumed by the frontend (types can be generated on the frontend side; the backend does not know about it).
- **Naming:** use cases are verbs (`StartBot`), ports are nouns (`OrderRepository`, `ExchangePort`), adapters name their technology (`SqlAlchemyOrderRepository`, `CcxtExchangeAdapter`).
- **Tests:** domain/application tests use in-memory fakes defined next to the ports (`fakes.py`), reused by e2e paper-mode tests.

## Incremental creation order

1. `core/` + `health` + Docker Compose + CI.
2. `market_data` + `exchanges` (public data) + `strategies` (protocol + one strategy).
3. `backtesting` + `analytics`.
4. `bots` + `trading` + `execution` (paper) + `portfolio` + `risk_management` + `audit`.
5. Testnet adapter, credential vault, reconciliation hardening.
6. Live adapter behind safeguards.
