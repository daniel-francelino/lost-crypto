# 01 — Technology Stack and Architectural Roles

Baseline as specified. Each technology is evaluated for its role, whether it is needed in the MVP, and the condition that justifies adopting it later.

| Technology | Architectural role | MVP? | Notes / adoption trigger |
|---|---|---|---|
| Python 3.12+ | Main language; `typing` (Protocol, Self, `type` aliases), `asyncio.TaskGroup` | Yes | — |
| FastAPI | Presentation layer only: HTTP, validation at the edge, OpenAPI contract for the frontend | Yes | Never imported by domain/application |
| Pydantic v2 | (a) API schemas, (b) settings via `pydantic-settings`, (c) validating strategy parameter schemas | Yes | Domain entities are plain dataclasses, not Pydantic models, to keep the domain framework-free. Pydantic is used at boundaries |
| SQLAlchemy 2.x | Persistence adapter (repositories). Async engine + `asyncpg` | Yes | ORM models live in infrastructure and are mapped to domain entities explicitly |
| Alembic | Schema migrations | Yes | Created at implementation time, not now |
| PostgreSQL | Source of truth; also the command/outbox channel in the MVP | Yes | `NUMERIC` for money; row locks and unique constraints enforce idempotency |
| Redis | Cache (rate-limit counters, last tick), pub/sub for live UI streaming, Celery broker | **No** | Adopt when (a) multiple workers need shared rate limiting, or (b) the UI needs push updates. Postgres `LISTEN/NOTIFY` + polling suffice first |
| Celery | Distributed job queue for heavy, short-lived work (large backtests, report generation) | **No** | Adopt when backtests must run in parallel/out of the worker. **Not** used for trading loops (see doc 07) |
| CCXT | Exchange adapter library behind the `ExchangePort`. Unifies REST, precision, market metadata. Async variant (`ccxt.async_support`); `ccxt.pro` (WebSockets) is a later option | Yes | Treated as an untrusted, leaky dependency: wrapped, never exposed beyond `infrastructure/` |
| Pandas | Historical data handling, indicators, backtest vectorised computations, analytics | Yes (backtest/analytics only) | Kept out of the domain; domain exchanges `Candle` value objects; adapters convert to DataFrames internally |
| NumPy | Numerical kernels for metrics (drawdown, Sharpe) | Yes (with Pandas) | — |
| Pytest | Unit, integration, contract and property tests; `pytest-asyncio` | Yes | Extra plugins only when needed |
| Ruff | Lint + format (replaces black/isort/flake8) | Yes | — |
| mypy | Static types, `strict` on domain/application | Yes | Strictness enforced per package |
| uv | Dependency management, lockfile, virtualenv | Yes | `pyproject.toml` + `uv.lock` |
| Docker | Reproducible image for `api` and `worker` (same image, different command) | Yes | — |
| Docker Compose | Local environment: `postgres`, `api`, `worker` (+ `redis` later) | Yes | Redis service added only when adopted |

## Justified additions (small, optional)

| Library | Why | When |
|---|---|---|
| `asyncpg` | SQLAlchemy async driver for PostgreSQL | MVP |
| `httpx` | HTTP test client and any non-CCXT HTTP calls | MVP (tests) |
| `structlog` (or stdlib `logging` + JSON formatter) | Structured logs with correlation ids | MVP; stdlib is acceptable to avoid a dependency |
| `cryptography` (Fernet / AES-GCM) | Encrypting stored exchange credentials | Before testnet/live |
| `tenacity` | Retry/backoff policies | Optional; a ~30-line helper may be enough |
| `pytest-cov`, `hypothesis` | Coverage; property tests for order math | Later, as needed |

Not adopted: ORMs besides SQLAlchemy, DI frameworks (manual composition root is enough), message brokers other than Redis, Kafka, TimescaleDB (reconsider only if candle volume becomes a bottleneck — see doc 08).

## Python version and typing policy

- Python 3.12+; `from __future__ import annotations` not required.
- `mypy --strict` for `domain/` and `application/`; relaxed for tests and thin adapters.
- No `float` in domain money fields (enforced by review and a lint/type convention: `Money`/`Decimal` value objects).
