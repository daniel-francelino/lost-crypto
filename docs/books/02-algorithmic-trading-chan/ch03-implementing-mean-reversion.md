# Book 2 · Chapter 3 — Implementing Mean Reversion Strategies

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 63–85 was read.

The author states that **none of the backtests in the book include transaction costs** and that some commit look-ahead by using the same data to fit parameters and test (p. 64). Every figure below inherits that caveat.

## 1. Chapter summary (pp. 63–85)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | True stationarity or cointegration is not required: short-term or seasonal mean reversion can be traded if you leave before the next equilibrium; and a stationary series with a 10-year half-life is not tradable. | Over-reliance on statistical tests. | 63 |
| C2 | **Spread, log-spread or ratio?** Price spread `y = Σ hᵢyᵢ` fixes the *number of shares*; log-price combination fixes *capital weights* and needs constant rebalancing (extra cost). A ratio is stationary only if hedge ratios are equal in magnitude, but works better when the pair is not truly cointegrated, and avoids a dynamic hedge ratio. Currency crosses are ratios by nature. In the GLD/USO example the price spread with a dynamic hedge ratio beat log-spread and ratio (APR 10.9% / 0.59 Sharpe vs 9% / 0.5 vs negative). | Choosing the signal. | 64–70 |
| C3 | **Bollinger-band strategy**: enter when the z-score of the spread exceeds `entryZscore` (below −entry → long), exit when it returns to `exitZscore` (< entry; 0 = mean; −entry = opposite band); look-back free or **set to the half-life**; at most one unit at a time, so capital and risk are easy to manage. GLD/USO: APR 17.8%, Sharpe 0.96 with entry 1, exit 0. | A practical, bounded version of the linear strategy. | 70–72 |
| C4 | **Scaling-in** (multiple bands): intuitive, but **Schoenberg & Corwin show that averaging-in is never optimal in-sample** when the probability of going lower is constant (worked example with L₁, L₂, F: all-in at L₁ expected `2(F−L₁)`; all-in at L₂ `2p(F−L₂)`; averaging `(F−L₁)+p(F−L₂)`; averaging is never the maximum). It can still help **out-of-sample** when volatility, hence *p*, changes, and it reduces market impact; scaling out gradually can still profit when the series is not truly stationary. | Whether to average in. | 72–74 |
| C5 | **Kalman filter as dynamic regression**: observable `y(t) = x(t)β(t) + ε`, hidden `β(t) = β(t−1) + ω` with identity state transition; iterative equations (3.7–3.13); it yields at once a dynamic hedge ratio, the *intercept* (replaces the moving average) and the forecast-error variance `Q(t)` (replaces the moving standard deviation). Parameters δ (here 0.0001) and `V_e` (0.001) chosen "with the benefit of hindsight". EWA/EWC example: APR 26.2%, Sharpe 2.4 (no costs). Avoids the abrupt effect of a fixed look-back window and an arbitrary weighting scheme. | Adaptive mean, spread and hedge ratio. | 74–82 |
| C6 | **Kalman filter as a single-series "market-making" model**: hidden mean `m(t)`, observed price `y(t)`; observation noise can be scaled by trade size (larger trade → more certainty), similar to a volume-and-time-weighted average price. | Adaptive fair-value estimate. | 82–83 |
| C7 | **Data errors inflate mean-reversion backtests** (a bad tick up is "shorted" and then "covered" for a fictitious profit) but *suppress* momentum backtests. Spreads amplify small quote errors (a $1 error on a $5 spread is 20%); the author saw losing live trades caused by a broker's data feed that vanished after switching provider. Bad ticks also trigger wrong live orders in either style. | Data quality. | 83–84 |
| C8 | Key points: price series for fixed shares, log series for fixed capital, ratios for currency pairs, Kalman or moving look-back for time-varying parameters, Bollinger bands with scaling-in as the practical form, data errors. | – | 85 |

The instruments are US ETFs and FX pairs traded long and short. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Bollinger-band / z-score strategy | ❌ | Not in the catalogue (`ema_crossover`, `donchian_breakout` only). No standard deviation or z-score helper exists in `strategies/domain`. |
| Look-back from the half-life | ❌ | Needs book 2 ch. 2 O1. |
| Scaling in/out | ❌ | One entry, one exit per round trip (the engine rejects a BUY while in position: `"already in position"` in `engine.py`). Partial orders are not modelled by the signal contract. |
| Kalman filter / adaptive mean | ❌ | None. |
| Spread/ratio/pair machinery | n/a | Single asset per bot, long-only. A ratio symbol such as ETH/BTC is a tradable single spot market (our adaptation), so *ratio mean reversion* is possible without a short leg. |
| Data-error protection, backtest | ❌ | No integrity check on stored candles (book 1 ch. 3 O3). |
| Data-error protection, live | ⚠️ | `max_candle_range_pct` (default 25%) rejects *entries* on suspect candles (`risk_management/domain/models.py`), and the trader only uses closed candles. The check is range-based only. |
| Costs included in backtests | ✅ | Fee and slippage are always applied in `run_backtest`, unlike the book's examples. |
| Same data for fit and test | ⚠️ | Train/test split exists; strategies with adaptive state (z-score look-back) run once across all data, which is correct as long as the state only uses past candles. |

## 3. Opportunities

### O1 — Long-only Bollinger/z-score mean-reversion strategy *(book: C3, pp. 70–72 · long-only crypto version is our adaptation)*
* **Problem:** the catalogue has no mean-reversion strategy, and the book calls this the practical form of the idea (bounded to one unit, so easy to size and risk-manage).
* **Proposal:** new strategy `bollinger_reversion`: long when `z < −entry_z` computed on closes over a `lookback`, exit when `z ≥ −exit_z` (default exit at the mean) or at an optional stop; parameters `lookback`, `entry_z`, `exit_z`, optional protective levels. Registered like existing strategies, no change to engine or signal contract (one entry, one exit).
* **Benefit:** a mean-reverting family that fits the present architecture; with book 2 ch. 2 diagnostics we can first check whether a crypto series reverts on the chosen timeframe.
* **Complexity:** low–medium (new strategy file, registry entry, catalogue, app parameter form, tests).
* **Risks:** long-only means it catches falling markets and never profits from the short side; the author notes stop-losses are not logical for this family while crypto crashes are large; three parameters to over-fit; fat tails make z-scores less meaningful; data errors inflate its backtest the most (C7). Must not ship without the data-integrity work from book 1 ch. 3 O3, the truncation test and cost sensitivity.
* **Validation:** truncation test; cost sweep; train/test; synthetic OU series where it must profit and a trending series where it must not; parameter sensitivity (a spike is overfit).

### O2 — Use the half-life as the default look-back; fewer free parameters *(book: C3, p. 70; ch. 2 C5)*
Pre-fill and bound `lookback` from the series half-life; document as a hint (the user can override). Depends on book 2 ch. 2 O1. Complexity low.

### O3 — Decide scaling-in only with evidence *(book: C4, pp. 72–74)*
* The book's result is that, **in-sample, a single entry level beats averaging in**, while real life with changing volatility can favour scaling. Our present one-entry model is therefore the book's recommended baseline. Do **not** add partial-order scaling now; revisit only if sweeps show a single-entry strategy suffers from entry timing and after the signal contract is extended for target sizes. Record as **B-SCALE-IN**.

### O4 — Adaptive mean/volatility via an exponential or Kalman estimator *(book: C5, C6, pp. 74–83)*
* **Proposal:** offer an EMA-based mean and variance (already used by the existing strategies for prices) and, later, a one-dimensional Kalman estimator (`m(t)`, `Q(t)`) as a drop-in replacement for the moving mean and standard deviation of O1, as the book argues it avoids the abrupt effect of a fixed window. The two-asset hedge-ratio version is out of scope.
* **Complexity:** medium (extra state; two noise parameters, which the author picks with hindsight). **Risk:** two more parameters to tune → snooping; the 1-D filter is a modest gain over an EMA. **Validation:** compare against EMA/rolling on synthetic data; sensitivity to δ and `V_e`. Low priority.

### O5 — Strengthen live bad-tick defence *(book: C7, pp. 83–84)*
* **Proposal:** beyond the range filter, add checks against the *previous close* (jump versus recent volatility) and against a second source (for example the exchange ticker versus the last candle close) before acting on a mean-reversion entry. **Complexity:** medium. **Risk:** more rejected legitimate crashes; tune carefully and log every rejection. Pair with book 1 ch. 3 O3.

### Not applicable / deferred
Pairs, spread/log-spread/hedge-ratio construction, Johansen/Kalman hedge ratios, currency crosses, market-making with trade-size-weighted noise (no tick data).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O5 live bad-tick defence | – | high | high | medium | book 1 ch. 3 O3 |
| 2 | O1 `bollinger_reversion` | medium | medium | – | low–medium | book 1 ch. 3 O3/O5, book 2 ch. 2 O1 |
| 3 | O2 half-life default | medium | – | – | low | book 2 ch. 2 O1 |
| 4 | O4 adaptive estimators | low | – | – | medium | O1 |
| 5 | O3 scaling-in | – | – | – | high | signal contract (B-SCALE-IN) |

## 5. Affected files
`strategies/domain/` (new strategy file, registry), `strategies/catalog.py`, `risk_management/domain/models.py` (O5), `market_data/domain/models.py`, app strategy parameter forms (`lib/shared/strategies/params.ts`) and labels, `check:consistency`, tests (`api/tests/unit`).

## 6. Incremental plan
1. Data integrity and truncation test first (book 1 ch. 3).
2. Diagnostics (book 2 ch. 2 O1) on real crypto series to check whether mean reversion exists at the intended timeframe.
3. If yes: `bollinger_reversion` with cost and sensitivity analysis; otherwise stop.
4. Live bad-tick checks.
5. Adaptive estimators only if the strategy proves useful.

## 7. Acceptance criteria and tests
* New strategy passes the truncation test and parameter validation like existing ones.
* It trades on synthetic mean-reverting data and stays flat or loses small on trending data in a test.
* Costs always included; results reported with train/test split and parameter-sensitivity view.
* No change to existing strategies or to live safeguards; ruff, mypy and tests green.

## Caveats
The book's APR and Sharpe figures (10.9%, 17.8%, 26.2%, etc.) come from ETF pairs traded long and short without costs, some with hindsight-chosen parameters. They cannot be expected on crypto. The claim that scaling-in is never optimal rests on a single stylised example with constant probabilities.
