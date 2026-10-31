# Book 2 · Chapter 2 — The Basics of Mean Reversion

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 39–62 was read.

## 1. Chapter summary (pp. 39–62)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Most price series are geometric random walks; **returns**, not prices, scatter around zero. Mean reversion of prices equals anti-serial-correlation of returns, which can be traded. The few stationary series are "prefabricated"; others can be **manufactured** by combining non-stationary series (cointegration). *Time-series* mean reversion (reverts to its own mean) vs *cross-sectional* (relative returns revert; Chapter 4). | Which series can be traded by reversion. | 39–41 |
| C2 | **Two equivalent views.** Mean reversion: next change proportional to (mean − current) → **ADF test** of whether that proportionality constant is zero. Stationarity: the variance of log prices grows slower than a random walk: `Var(τ) ∝ τ^(2H)`, **Hurst exponent H < 0.5** means reverting, 0.5 random walk, > 0.5 trending → **Variance Ratio test** of H = 0.5. "Stationary" does not mean range-bound. | Statistical tests. | 41, 44–45 |
| C3 | **ADF**: regress `Δy(t)` on `y(t−1)` (plus lagged differences); the statistic is `λ / SE(λ)`, must be negative and below Dickey–Fuller critical values (depend on sample size and on whether a constant/drift is included; drift assumed zero in practice). Example: USD.CAD statistic −1.84 vs 90% critical −2.594: not stationary. | Testing mean reversion. | 42–44 |
| C4 | **Hurst/variance ratio** example: USD.CAD H = 0.49, p-value 0.367: cannot reject a random walk. | Testing stationarity. | 44–46 |
| C5 | **Half-life**: with `Δy = λ·y(t−1) + μ + ε` as an Ornstein–Uhlenbeck process, the expected price decays exponentially to `−μ/λ` with **half-life = −ln(2)/λ**. If λ > 0, do not write a mean-reversion strategy; if λ ≈ 0, few round trips; the half-life gives a **natural time scale** (look-back ≈ a small multiple of the half-life), which avoids brute-force optimising a look-back. The statistical tests are very demanding (≥ 90%); practical profitability needs less certainty. USD.CAD half-life ≈ 115 days. | How fast it reverts and what look-back to use. | 46–48 |
| C6 | **Linear mean-reverting strategy** (parameterless): hold a number of units **proportional to the negative z-score** (price minus moving average over moving standard deviation), with look-back = half-life. The author flags problems of his own example: look-ahead through the in-sample half-life, no cap on capital, no costs. The point: preliminary tests use every bar so they have more statistical power than a backtest with few round trips. | Strategy without optimisation. | 48–50 |
| C7 | **Cointegration**: a stationary linear combination of non-stationary series. **CADF** (Engle–Granger): regress one series on the other to get the hedge ratio, test the residual; the result depends on which series is the regressor. EWA/EWC statistic −3.64 vs 5% critical −3.359. **Johansen** test: any number of series, order-independent; returns the number of cointegrating relations and eigenvectors usable as hedge ratios (largest eigenvalue → shortest half-life). EWA-EWC-IGE portfolio half-life ≈ 23 days; linear strategy APR 12.6%, Sharpe 1.4 (no costs). | Building stationary portfolios. | 50–60 |
| C8 | **Pros/cons**: many choices and often a fundamental story for why a pair cointegrates (and why it broke); short time scales give many trades (statistical confidence); but consistency breeds **overconfidence and overleverage** (LTCM); a breakdown hits at maximum leverage; **stop-losses cannot be logically deployed** (risk handling in Chapter 8). | Risks of the style. | 60–61 |

The chapter's instruments are currencies and ETFs, with long and short legs. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Mean-reversion strategies | ❌ | Only trend/breakout strategies exist (book 1 ch. 7). |
| Stationarity/mean-reversion tests (ADF, Hurst, VR) | ❌ | No statistical module for time series; `analytics/domain/metrics.py` only holds performance metrics. |
| Half-life | ❌ | Not computed (also proposed in book 1 ch. 7 O3; this chapter gives the full recipe). |
| Cointegration (CADF/Johansen) | ❌ and unusable as is | Requires a short leg and multiple assets per bot. |
| Look-back choice | ⚠️ | Look-backs are user parameters (`fast_period`, `slow_period`, `entry_period`...), optimised by sweeps, which is exactly the brute-force approach C5 tries to avoid. |
| Parameterless/linear sizing | ❌ | Sizing is all-in or `max_position_fraction`; no position proportional to a signal. |
| Overconfidence control | ✅ partly | Live caps, daily-loss and drawdown pauses exist (see book 1 ch. 6). |

## 3. Opportunities

### O1 — Research statistics module: ADF, variance ratio, Hurst, half-life *(book: C2–C5, pp. 41–48)*
* **Problem:** we cannot tell, before backtesting, whether a symbol/timeframe shows trending, random or mean-reverting behaviour, and sweeps are used as a substitute.
* **Proposal:** pure functions, on log-prices/prices of a stored candle series: ADF statistic with the Dickey–Fuller critical values, half-life `−ln2/λ`, Hurst exponent via the variance relation, and the variance-ratio statistic. Expose as a read-only "series diagnostics" endpoint and a panel in the market-data page ("Does this pair trend or revert on this timeframe?"). Report `None` when the sample is too small or the regression is degenerate.
* **Benefit:** tells the operator which family of strategy fits a pair/timeframe and what look-back is natural, with far more statistical power than a backtest (C6 reasoning, p. 50). It would also allow checking the book 1 ch. 7 claim ("mean reversion more prevalent") on crypto instead of assuming it.
* **Complexity:** medium (OLS, a small linear solve, critical-value tables; decimal vs float boundary must be decided because the tests need `sqrt`, `log` and regression; the rule "money is never float" covers money, not statistics, but keep a single documented conversion point). The Johansen test is *not* included.
* **Risks:** crypto series are fat-tailed, volatile and heteroskedastic; an ADF "pass" in one window may not persist; the critical values depend on the exact model (constant, no drift). Overlapping candles at 1 minute are not independent observations: sample at the strategy's horizon (the author samples daily closes from minute bars, p. 43).
* **Validation:** synthetic Ornstein–Uhlenbeck series with known λ (half-life recovered within tolerance), random walks (should not reject), trending series (H > 0.5); reproduce the book's `−log(2)/λ` identity; determinism.

### O2 — Natural time scale from the half-life to cut brute-force sweeps *(book: C5, p. 47)*
* **Proposal:** when a strategy has a look-back parameter, show the series half-life next to it as a suggested range and let sweeps default to a narrow multiple of it. **Complexity:** low once O1 exists. **Risk:** only meaningful for mean-reverting strategies; for trend strategies the half-life of a trending series is undefined (λ ≥ 0) and the UI must say so. **Validation:** UI/API test with a synthetic series.

### O3 — Parameterless linear mean-reversion strategy, long-only *(book: C6, pp. 48–50)*
* **Proposal:** a strategy that holds a fraction of the position budget proportional to `max(0, −z)`, with look-back equal to the half-life, so it has no tunable parameter besides the look-back it derives itself; long-only means it can only scale in below the mean and out above. The book's version also shorts and has no cap; ours must cap exposure through the existing risk module.
* **Problem it solves:** a first mean-reversion entry in the catalogue without a parameter hunt.
* **Complexity:** medium: today strategies emit discrete BUY/SELL signals for one position; a proportional/scaled position requires either multi-step partial orders (the engine supports one buy then one sell) or a signal carrying a target size, which touches the signal contract, the engine and the risk module. That is a bigger change than the strategy file itself.
* **Risks:** the author notes his example uses an in-sample half-life (look-ahead) and needs unlimited capital; no stop-loss is logical for this family (C8); long-only loses half the edge and is prone to catching a falling market. 
* **Validation:** truncation test (book 1 ch. 3 O5) with the half-life estimated only from the prefix; cost sensitivity; test-segment results. Treat as a *later* item, after O1 shows crypto pairs actually revert on some timeframe.

### O4 — Warn when a mean-reversion strategy is paired with a stop-loss or unlimited scaling *(book: C8, p. 61, ties to book 1 ch. 6 C9)*
* **Proposal:** strategy metadata flag `family = mean_reversion`, with a UI warning on stop-loss and a requirement to set exposure caps. **Complexity:** low. Do after O3.

### Not applicable / deferred
Cointegration tests (CADF, Johansen) and pair/triplet portfolios: the system is spot long-only with one asset per bot. One crypto-specific possibility that fits the current architecture is testing stationarity of **a tradable ratio symbol** such as ETH/BTC (a single spot market whose price already *is* the ratio), which makes a "pair" tradable with one position. That idea is ours, not the book's; it needs O1 first and does not require a short leg.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 diagnostics (half-life first, then ADF/VR/Hurst) | high | – | – | medium | – |
| 2 | O2 time-scale hint | medium | – | – | low | O1 |
| 3 | O4 family warning | low | medium | – | low | strategy metadata |
| 4 | O3 linear strategy | medium | medium | – | medium–high | O1, signal contract change |

## 5. Affected files
New pure module under `analytics/domain/` (series statistics), `market_data/presentation/router.py` (diagnostics endpoint), `docs/openapi.json`, `strategies/domain/base.py` (family metadata), `backtesting/domain/engine.py` and `strategies/domain/types.py` (only for O3), app market-data page and chart rows (`lib/market-data/`), `check:consistency`, tests in `api/tests/unit`.

## 6. Incremental plan
1. Half-life and Hurst/variance ratio on a stored series (no UI), with synthetic-series tests.
2. ADF with critical values; diagnostics endpoint; app panel.
3. Time-scale hint in the strategy forms.
4. Family metadata and warnings.
5. Decide on O3 after reading what the diagnostics say about real pairs.

## 7. Acceptance criteria and tests
* Synthetic OU series with half-life *h*: estimate within a stated tolerance; random walk: no rejection at the stated level in most runs; trend: H > 0.5.
* Diagnostics return `None` with an explicit reason on short or constant series; never NaN or infinity.
* No change to existing strategies, signals, risk or live behaviour; ruff, mypy, existing tests green.
* UI copy states that a statistical pass is not a profit guarantee.

## Caveats
Every performance number here (APR 12.6%, Sharpe 1.4, half-lives of 115 and 23 days) comes from pre-2013 currency and ETF examples, **without transaction costs** (p. 49), partly in-sample, and says nothing about crypto. The author himself calls the example strategy impractical (p. 50).
