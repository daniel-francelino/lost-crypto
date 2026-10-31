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
| Parameter search | Sweeps exist (API/UI). With a split they rank by the **train** part and show the test part as a check (`rank_by` overrides); they report `trials`, an approximate `prior_trials` count and a neighbour-based robustness verdict (plateau / peak). No statistical correction for the number of trials (no PSR/DSR/PBO). |
| Robustness | Optional cost ladder (fee + slippage × 0–3, break-even), metrics by calendar year/quarter (`periods.py`), operator drawdown tolerance flag. |
| Reproducibility | `seed` and a SHA-256 of the candles are recorded per run. The fill model is deterministic. |
| Data | Candles stored in Postgres, imported by manual jobs. Invalid candles (OHLC inconsistent, non-positive price, negative volume, misaligned time) are not imported and are skipped by the bots' trader with an audit event (`market_data/domain/quality.py`); re-imports count changed candles. Outlier report (> 4σ). The risk module still refuses entries on suspect candles (`max_candle_range_pct`). A daily listing snapshot records first-seen/delisted dates from now on; earlier delistings are unknown. |
| Gaps | Backtests refuse ranges missing > 1% of candles or with a hole > 24 h unless `allow_gaps`; gaps, invalid candles, outliers and the sample-size check are stored in `data_quality`. The engine fills a signal at the next available open after a hole. |
| Look-ahead | Truncation test over every catalog strategy (`tests/unit/test_lookahead.py`), with a leaky control. |

## Metrics (`modules/analytics/domain/metrics.py`)

Net PnL, total return %, buy-and-hold return %, max drawdown %, fees paid, fills, round trips, win rate, profit factor, average trade PnL, open-position flag, rejected signals. Since book 1 ch. 2: Sharpe, Sortino, information ratio vs. holding the asset, annualised return and volatility (365-day year, risk-free 0, `None` below 30 returns or 30 days; `risk_ratios.py`), exposure, sample size and gaps, drawdown duration, peak/trough, current and open drawdown. Same functions for backtests and bots.

**Not computed:** Calmar, trade-level distribution (skew, kurtosis, tails), confidence intervals, any significance test (PSR/DSR).

## Risk (`modules/risk_management`)

Per bot: position fraction, max order notional, daily loss %, drawdown %, consecutive losses, risk-per-trade sizing from the stop, required stop, suspect-candle filter. Global: max open positions and max exposure. Live: hard caps from the environment, kill switch, typed-name single-use approval, minimum paper days. Exits are always allowed.

## Operations

* Worker supervises bots, reconciles every 60 s, writes a heartbeat. The API exposes worker liveness and stale bots.
* The trader fetches recent candles itself each cycle; **historical import is manual**.
* **No alerting or notification channel exists** (no webhook, email, chat). Failures are visible only to someone looking at the UI.
* Audit log for state changes, orders and approvals.

## Frontend

`app/` (TanStack Start SPA, zod, lost-ui). Shows what the API exposes; no business rules.

## Known absences worth remembering when reading the books

Portfolio-level optimisation (Kelly, covariance), multiple concurrent strategies per capital pool, regime detection, cross-validation beyond one split, cost models that depend on size or volatility, funding/borrow costs, short selling, mean-reversion/pairs/stat-arb strategies, machine-learning pipelines, labelling and meta-labelling.
