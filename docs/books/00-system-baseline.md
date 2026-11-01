# 00 — System baseline (what Lost Crypto does today)

Verified in the code on 2026-10-31. Every chapter report compares the book against this file; update it when the code changes, so the reports stay honest.

## Scope

* Spot only, **long-only**, one position per bot. No leverage, margin, futures or shorting.
* Exchange: Binance (spot and testnet) behind a single `ExchangeRegistry`. Candle timeframes are time-based (no volume/tick bars).
* Strategies: `ema_crossover`, `donchian_breakout`, `trend_quality_breakout` (trend; since the books 3+4 synthesis: Donchian entry gated by the efficiency ratio, ATR stop, no profit target) and `mean_reversion_zscore` (mean reversion, since book 2 ch. 3), each with a `StrategyStyle` (`api/src/modules/strategies/domain/`). Strategies emit *intents*; sizing and risk are elsewhere.

## Backtesting (`modules/backtesting`)

| Aspect | Today |
|---|---|
| Timeline | Signal after candle *i−1* closes is filled at the **open** of candle *i*; no look-ahead in the loop (`engine.py`). |
| Costs | Fixed `fee_rate` and fixed `slippage_bps` per run, applied on every fill. Same fill code as the paper trader (`execution/domain/fills.py`). |
| Stops | Stop/target checked against the candle low/high; stop wins when both are inside the candle; a gap through the stop fills at the open (`risk_management/domain/stops.py`). |
| Sizing | All cash in by default. Optionally (`risk`) the backtester uses the bot's risk module (`assess_signal` sizing and the daily-loss / drawdown / consecutive-loss pauses) and `fill_timing=signal_close`, as the bots do. |
| Parity | Bots store every candle they process; `POST /bots/{id}/parity` replays the latest session through the backtester and classifies differences; live readiness needs a recent parity with none unexplained. Orders keep the reference price and times (realized slippage, latency). |
| Out-of-sample | One chronological split (`test_fraction`), strategy runs once over all data, metrics reported for train and test (`segments.py`). |
| Parameter search | Sweeps exist (API/UI). With a split they rank by the **train** part and show the test part as a check (`rank_by` overrides); they report `trials`, an approximate `prior_trials` count and a neighbour-based robustness verdict (plateau / peak). No statistical correction for the number of trials (no PSR/DSR/PBO). |
| Robustness | Optional cost ladder (fee + slippage × 0–3, break-even), metrics by calendar year/quarter (`periods.py`), operator drawdown tolerance flag. |
| Reproducibility | `seed` and a SHA-256 of the candles are recorded per run. The fill model is deterministic. |
| Data | Candles stored in Postgres, imported by manual jobs. Invalid candles (OHLC inconsistent, non-positive price, negative volume, misaligned time) are not imported and are skipped by the bots' trader with an audit event (`market_data/domain/quality.py`); re-imports count changed candles. Outlier report (> 4σ). The risk module still refuses entries on suspect candles (`max_candle_range_pct`). A daily listing snapshot records first-seen/delisted dates from now on; earlier delistings are unknown. |
| Gaps | Backtests refuse ranges missing > 1% of candles or with a hole > 24 h unless `allow_gaps`; gaps, invalid candles, outliers and the sample-size check are stored in `data_quality`. The engine fills a signal at the next available open after a hole. |
| Look-ahead | Truncation test over every catalog strategy (`tests/unit/test_lookahead.py`), with a leaky control. |

## Metrics (`modules/analytics/domain/metrics.py`)

Net PnL, total return %, buy-and-hold return %, max drawdown %, fees paid, fills, round trips, win rate, profit factor, average trade PnL, open-position flag, rejected signals. Since book 1 ch. 2: Sharpe, Sortino, information ratio vs. holding the asset, annualised return and volatility (365-day year, risk-free 0, `None` below 30 returns or 30 days; `risk_ratios.py`), exposure, sample size and gaps, drawdown duration, peak/trough, current and open drawdown. Same functions for backtests and bots.

Since book 2 ch. 8: the maximum adverse excursion of each backtest trade (`excursion`, migration `0019`), an advisory exposure curve (`/backtests/{id}/exposure-curve`), a `protective_exit_slippage` alert for stops that fill far worse than configured, and `drawdown_action` (`pause` default | `stop`, migration `0020`) on a bot's risk limits.

Since book 2 ch. 7: an optional backtest slippage model (`volatility_size`, migration `0018`) on top of the fixed one, which stays the default and what bots and parity use.

Since book 2 ch. 6: a lagged-return correlation grid (`/market-data/momentum-grid`, non-overlapping samples, Bonferroni-corrected) and start-date sensitivity sweeps (`start_offset_days` in a sweep grid).

Since book 2 ch. 5: named regime breaks (`regime_breaks`, operator-registered, never edited) and per-stretch metrics of each backtest between the breaks that fall inside it (`break_metrics`, with a snapshot of the breaks used).

Since book 2 ch. 2: Hurst exponent, variance ratios (lags 2, 4, 8), optional sampling every N candles and suggested look-back windows around the half-life, all descriptive and served by `/market-data/half-life`.

Since book 2 ch. 1: `sharpe_t_stat` and `significance_p` (Gaussian test, one-sided table 0.10 to 0.001, `analytics/domain/significance.py`); each backtest also stores a random-entries test (`significance` JSONB, migration `0015`, 1,000 seeded simulations, needs 10 trades) and the detail reports `prior_runs`. `GET /bots/{id}/backtest-comparison` compares a bot's realized Sharpe with its equivalent backtest.

**Not computed:** Calmar, trade-level distribution (skew, kurtosis, tails), confidence intervals, PSR/DSR and any multiple-testing correction.

## Risk (`modules/risk_management`)

Per bot (book 2 ch. 3 added `max_close_jump_pct`, off by default: refuses entries after a close-to-close jump, never exits): position fraction, max order notional, daily loss %, drawdown %, consecutive losses, risk-per-trade sizing from the stop, required stop, suspect-candle filter. Global: max open positions and max exposure. Live: hard caps from the environment, kill switch, typed-name single-use approval, minimum paper days. Exits are always allowed.

## Operations

* Worker supervises bots, reconciles every 60 s, writes a heartbeat. The API exposes worker liveness and stale bots; `GET /health/worker` (200/503, no login) serves an external monitor and the worker's Docker healthcheck.
* Live keys are verified at creation and re-checked daily; a key that turns unacceptable blocks new entries (exits continue). The status lists exchange positions without a native stop, the clock skew with the exchange (> 5 s blocks new live entries) and the backup state (`manage backup` / `restore-check`). Runbook: `api/docs/operations/runbook.md`.

* The trader fetches recent candles itself each cycle. Since the Chapter 1 work, the worker also **extends stored candles** (closed candles only, series already stored and recent, or used by a bot) and **historical import stays manual**.

* **Alerts are in-app only** (`notifications` module, `/alerts`, indicator in the top bar): worker down (raised by the API process), bot stale/error, kill switch, stale candles, exchange rate limiting and, since book 2 ch. 4, `performance_degraded` (a running bot whose realized Sharpe is below half of its backtest's, or whose current drawdown exceeds the backtest's maximum, after 30+ live returns; a warning that never pauses the bot). No external channel (webhook, email, chat) exists. Free-text analysis notes on bots and backtests are audit events (`note.added`).

* Audit log for state changes, orders and approvals. Bot pause/stop/reset commands and config edits record the authenticated actor and optional reason; edits record safe before/after values. `GET /api/v1/bots/{id}/interventions?days=30` reports intervention counts, recent items and drawdown context (5% threshold); overview cards show the 30-day count. The UI confirms edits and requests a reason when the bot has orders.

## Frontend

`app/` (TanStack Start SPA, zod, lost-ui). Shows what the API exposes; no business rules.

## Known absences worth remembering when reading the books

Portfolio-level optimisation (covariance; Kelly remains an advisory backtest reference), multiple concurrent strategies per capital pool, cross-validation beyond one split, cost models that depend on size or volatility, funding/borrow costs, short selling, mean-reversion/pairs/stat-arb strategies, machine-learning pipelines, labelling and meta-labelling. Historical regime descriptors and tail-loss sizing are available for backtests; they are descriptive advisories and no sizing suggestion is applied to orders.
