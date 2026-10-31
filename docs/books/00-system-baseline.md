# 00 — System baseline (what Lost Crypto does today)

Verified in the code on 2026-10-31. Every chapter report compares the book against this file; update it when the code changes, so the reports stay honest.

## Scope

* Spot only, **long-only**, one position per bot. No leverage, margin, futures or shorting.
* Exchange: Binance (spot and testnet) behind a single `ExchangeRegistry`. Candle timeframes are time-based (no volume/tick bars).
* Strategies: `ema_crossover` and `donchian_breakout` (`api/src/modules/strategies/domain/`). Strategies emit *intents*; sizing and risk are elsewhere.

## Backtesting (`modules/backtesting`)

| Aspect | Today |
|---|---|
| Timeline | Signal after candle *i−1* closes is filled at the **open** of candle *i*; no look-ahead in the loop (`engine.py`). |
| Costs | Fixed `fee_rate` and fixed `slippage_bps` per run, applied on every fill. Same fill code as the paper trader (`execution/domain/fills.py`). |
| Stops | Stop/target checked against the candle low/high; stop wins when both are inside the candle; a gap through the stop fills at the open (`risk_management/domain/stops.py`). |
| Sizing | Trivial: all cash in, whole position out. Real sizing lives in the risk module and is **not** used by the backtester. |
| Out-of-sample | One chronological split (`test_fraction`), strategy runs once over all data, metrics reported for train and test (`segments.py`). |
| Parameter search | Sweeps exist (API/UI), results ranked per run. No correction for the number of trials. |
| Reproducibility | `seed` and a SHA-256 of the candles are recorded per run. The fill model is deterministic. |
| Data | Candles stored in Postgres, imported by manual jobs; suspect candles are refused at entry by the risk module (`max_candle_range_pct`). Delistings/survivorship are not modelled. |

## Metrics (`modules/analytics/domain/metrics.py`)

Net PnL, total return %, buy-and-hold return %, max drawdown %, fees paid, fills, round trips, win rate, profit factor, average trade PnL, open-position flag, rejected signals.

**Not computed:** Sharpe/Sortino, annualised return, drawdown *duration*, volatility, exposure/time in market, Calmar, trade-level distribution (skew, kurtosis, tails), confidence intervals, any significance test.

## Risk (`modules/risk_management`)

Per bot: position fraction, max order notional, daily loss %, drawdown %, consecutive losses, risk-per-trade sizing from the stop, required stop, suspect-candle filter. Global: max open positions and max exposure. Live: hard caps from the environment, kill switch, typed-name single-use approval, minimum paper days. Exits are always allowed.

## Operations

* Worker supervises bots, reconciles every 60 s, writes a heartbeat. The API exposes worker liveness and stale bots.
* The trader fetches recent candles itself each cycle. Since the Chapter 1 work, the worker also **extends stored candles** (closed candles only, series already stored and recent, or used by a bot) and **historical import stays manual**.
* **Alerts are in-app only** (`notifications` module, `/alerts`, indicator in the top bar): worker down (raised by the API process), bot stale/error, kill switch, stale candles and exchange rate limiting. No external channel (webhook, email, chat) exists.
* Audit log for state changes, orders and approvals.

## Frontend

`app/` (TanStack Start SPA, zod, lost-ui). Shows what the API exposes; no business rules.

## Known absences worth remembering when reading the books

Portfolio-level optimisation (Kelly, covariance), multiple concurrent strategies per capital pool, regime detection, cross-validation beyond one split, cost models that depend on size or volatility, funding/borrow costs, short selling, mean-reversion/pairs/stat-arb strategies, machine-learning pipelines, labelling and meta-labelling.
