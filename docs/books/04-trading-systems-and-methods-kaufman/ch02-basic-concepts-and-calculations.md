# Book 4 · Chapter 2 — Basic Concepts and Calculations

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20; some symbols lost in the text). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 25–55 and 58–61 were read. The index-construction detail (pp. 55–58), the remainder of the probability section (pp. 62–66: runs, expectation and so on) and "Supply and Demand" (pp. 66–78) were **not** read in detail and are not summarised.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Law of averages** correctly understood: abnormal runs do not need to be "offset"; normal events overwhelm them. | Gambler's fallacy. | 26 |
| C2 | **In-sample / out-of-sample**: all testing is overfitting; keep unseen data; **you get one chance**: if the out-of-sample run fails you are done; changing the rules after looking contaminates it. Alternating 2-year blocks may help markets that change; with half the data withheld you only get half the patterns. | Honest validation. | 27–28 |
| C3 | **Sample error ≈ 1/√N**: 1 item → 100%; 4 → 50%; **400 trades → 5%**. A slow system with 2–3 trades a year needs the same method applied across many markets to reach a useful N. | How many trades are enough. | 28–29 |
| C4 | **Representative data**: at least one bull, one bear and some sideways periods (10 years of a bull market make any long strategy look good); structural changes (a company, a currency) can make old data unrepresentative; longer samples help adaptivity checks; many daily trades do not cover varied conditions. | Data coverage. | 29 |
| C5 | **Averages**: arithmetic, time-weighted, geometric (for ratios and percentage changes), quadratic (RMS), harmonic, median, mode; each fits different data. | Right average for the job. | 30–37 |
| C6 | **Moments**: mean, variance/standard deviation, **skewness** (price data are positively skewed, trading profits of trend systems with fixed stops are skewed right), **kurtosis** (excess = K − 3). **Kurtosis of daily returns above 7–8 begins to look like overfitting**: "an overwhelming number of profitable trades of similar size, which is not likely to happen in real trading". Standard deviation misleads for skewed data; frequency distributions (percentiles) are better. No normal distribution in trading. | Shape of results. | 37–43 |
| C7 | **Autocorrelation** (persistence) via lagged correlation or the Durbin–Watson d-statistic (2 = none). **Two-sample t-test** of consistency: compare the means of two *non-overlapping* periods of a system's **net trade returns** using Satterthwaite degrees of freedom. | Detecting persistence; checking stability of results. | 43–48 |
| C8 | **Standardise risk and return**: annualise; compare at a common **target volatility** (the book uses 12%; scale exposure by actual/target volatility). Returns: standard `p₁/p₀ − 1` vs `ln` returns (small differences compound); NAV starts at 100; AROR simple `(E_n/E₀ −1)·252/n` and compounded `(E_n/E₀)^(252/n) − 1`; use 252 for trading days. Annualise standard deviation by multiplying by the **square root** of the number of observations per year (the text shows "multiply by 252" in one place, which contradicts this rule and the later paragraph). | Comparable numbers. | 48–53 |
| C9 | **Monthly data always looks less volatile** than daily (S&P 1990–2010: 18.6% daily vs 15.3% monthly), hiding mid-month drawdowns; due diligence asks for daily returns. | Understated risk. | 53 |
| C10 | **Downside risk**: semivariance / lower partial moments; drawdown-based risk (net loss on days below the equity peak). | Risk that matters. | 53–54 |
| C11 | **Performance ratios**: information ratio (return/risk), Sharpe (excess over the risk-free rate), Treynor (beta), **maximum drawdown** (percentage from peak NAV to the lowest later NAV; keeps single large drawdowns visible), **Calmar** (return / max drawdown), **Sortino** (downside deviation); simplest measures are usually best and most rank candidates similarly. Beta/alpha from regression against an index; the index is the benchmark (60/40 stock-bond portfolio). | Ranking systems. | 52, 58–59 |
| C12 | **Probability** basics: addition/multiplication rules, joint, marginal and contingent probability (example of two-day up/down sequences). | Conditional reasoning. | 59–61 |

Examples are futures and equity indices. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| One-chance out-of-sample discipline | ❌ | The test segment can be inspected for any number of runs (book 3 ch. 6, ch. 9 O2). |
| Trade-count / sample-error awareness | ⚠️ | `round_trips` shown; no warning relative to 1/√N or to a target (book 1 ch. 3 O6, book 3 ch. 4 O5). |
| Representative regime coverage | ❌ | No check that the window includes rising, falling and sideways phases; a long-only strategy tested on a bull run is not flagged. |
| Skewness / kurtosis / percentiles of results | ❌ | `Metrics` has none; no distribution of trade or bar returns. |
| Kurtosis red flag | ❌ | None. |
| Autocorrelation, Durbin–Watson | ❌ | None (also book 2 ch. 6 O1). |
| Two-sample t-test between periods (train vs test) | ❌ | Train and test metrics are shown side by side without any test of whether they differ. |
| Target-volatility normalisation of results | ❌ | Results are in absolute return; comparing a volatile and a calm pair is not normalised. |
| Return conventions | ⚠️ | Equity-based returns in `Decimal`; log vs simple not documented (book 3 ch. 1 O4). |
| Daily vs monthly volatility | n/a | Metrics are not volatility-based yet. |
| Downside risk / Sortino / Calmar / drawdown stats | ❌ | Only `max_drawdown_pct` (book 1 ch. 2). |
| Max drawdown definition | ✅ | `max_drawdown_pct` = percentage from running peak, as defined. |

## 3. Opportunities

### O1 — Richer metrics set aligned with the chapter *(book: C6, C8, C10, C11, pp. 38–59)*
* **Proposal:** extend the metrics module with Sortino (downside deviation), **Calmar** (annualised return / max drawdown), skewness and excess kurtosis of per-bar and per-trade returns, percentiles of trade returns, and standard deviation computed **from bar returns at the strategy's bar frequency**, annualised with `√(bars per year)` (the convention book 1 ch. 3 O1 fixed for 24/7 markets). Include the sample size with each.
* **Benefit:** completes the performance picture the books keep asking for (risk-adjusted, downside-aware). **Complexity:** low–medium (pure `Decimal` functions with a documented float boundary for `sqrt`).
* **Risks:** each added ratio invites cherry-picking; show a fixed, small set. Sample moments of skewness and kurtosis are unstable with few trades. **Validation:** hand-computed fixtures (including Table 2.3 style data); property tests.

### O2 — Overfitting heuristic: kurtosis and similar-sized profits *(book: C6, p. 43)*
Flag runs whose per-bar (or per-trade) return distribution has excess kurtosis above a configurable threshold (the author cites about 7–8 as suspicious) and/or an unusually high share of near-identical profitable trades, as part of the red-flag block (book 2 ch. 1 O3). The author's threshold is a heuristic from experience, not a statistical test. **Complexity:** low. **Validation:** synthetic overfit-like series.

### O3 — Two-sample comparison of train vs test trade returns *(book: C7, p. 48)*
* **Proposal:** a Welch/Satterthwaite two-sample t-test (and a bootstrap alternative) on the net returns of train-segment trades vs test-segment trades, reported with sample sizes, to answer "is the test period different from the train period?" in a statistical sense. **Benefit:** replaces eyeballing two columns. **Complexity:** low. **Risks:** few trades; fat tails; the test checks *difference*, not *skill*; combine with book 3 ch. 5 (permutation). **Validation:** synthetic samples with known mean difference.

### O4 — Target-volatility normalisation for comparisons *(book: C8, pp. 52–53)*
Report each run also at a **target annualised volatility** (the book's 12%): `scale = target / realised volatility`, applied to the return series (exposure scaling, capped at 1 because spot long-only; therefore only meaningful for *deleveraging*, i.e. when realised volatility exceeds the target). Useful to compare a strategy on BTC with one on a smaller coin. **Complexity:** low. **Risk:** the cap at 1 means low-volatility results cannot be scaled up; label clearly.

### O5 — Regime-coverage check on the data window *(book: C4, p. 29)*
For a backtest window, classify the buy-and-hold path into rising / falling / sideways thirds (for example by rolling return relative to a band), and warn when any class is under-represented; for long-only strategies, warn if the window is overwhelmingly a bull market. Heuristic classification is **our adaptation**; the book states the principle. **Complexity:** low–medium. Pairs with named regime breaks (book 2 ch. 5 O1).

### O6 — Make the one-chance rule explicit *(book: C2, p. 27)*
Already covered by the validation-lock proposal (book 3 ch. 9 O2). Add the book's rule to the runbook: a failed validation ends the idea; re-tuning after seeing it contaminates the data. **Complexity:** documentation.

### O7 — Document return and annualisation conventions *(book: C8, pp. 49–53)*
Write down in `docs/` which returns (simple vs log), which day count (calendar 365 for crypto), and which volatility annualisation the system uses, resolving the conflict between the book's statements (the "multiply by 252" sentence vs the square-root rule). **Complexity:** very low.

### Not applicable
Construction of price indexes, averages for commodity prices, joint-probability exercises.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O7 conventions note | medium | – | – | very low | – |
| 2 | O1 richer metrics | high | high | – | low–medium | book 1 ch. 2 O1 |
| 3 | O2 kurtosis flag | medium | – | – | low | O1 |
| 4 | O3 train vs test t-test | medium | – | – | low | O1 |
| 5 | O5 regime coverage | medium | – | – | low–medium | – |
| 6 | O4 target-volatility view | low | medium | – | low | O1 |
| 7 | O6 runbook rule | – | – | – | none | – |

## 5. Affected files
`analytics/domain/metrics.py`, `analytics/domain/inference.py`, `backtesting/domain/segments.py`, `analytics/presentation/schemas.py`, `docs/openapi.json`, `docs/` conventions note, app metric cards, tests (`api/tests/unit`).

## 6. Incremental plan
1. Conventions note.
2. Pure functions: Sortino, Calmar, skewness, kurtosis, percentiles.
3. Train-vs-test comparison and kurtosis flag.
4. Regime coverage warning and target-volatility view.

## 7. Acceptance criteria and tests
* Hand-computed fixtures for every new metric; `None` with a reason for degenerate or short series.
* All additions are optional/additive in the API; stored runs unaffected; ruff, mypy, existing tests green.

## Caveats
The book's thresholds (400 trades for 5% error, kurtosis above 7–8, 12% target volatility) are the author's conventions for futures. A 1/√N error is a rule of thumb that assumes independent trades.
