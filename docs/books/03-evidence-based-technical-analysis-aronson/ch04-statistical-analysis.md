# Book 3 · Chapter 4 — Statistical Analysis

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 165–175 and 186–189 and 202–216 were read in full. The textbook-style middle (pp. 176–185 box-of-beads experiments, 190–201 descriptive statistics, probability and distributions) was read by heading and skimmed; nothing technical specific to trading was found there beyond what the later sections restate.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | The essence of TA is **statistical inference**: generalise from historical samples to the future. Start with the **null hypothesis**: the rule has no predictive power and its expected return is zero **on detrended data**; a profitable back test is "luck" until shown otherwise. | Default skepticism. | 165–167 |
| C2 | **Reading evidence**: the p-value is the share of the null's probability density at or beyond the observed performance; it speaks to the *likelihood of the evidence under the null*, not the probability that the hypothesis is true. The convention is **0.05**. Affirming the consequent is invalid; denying the consequent is valid. | Interpreting significance. | 167–171 |
| C3 | **Data mining raises the bar**: when the best of many rules is picked, the appropriate null distribution is that of the *best of 1,000* rules, wider than the single-rule one; an excellent single-rule result is mediocre as the best of 1,000 (Figure 4.4; Chapter 6). | Multiple testing. | 171–172 |
| C4 | **Six elements of an inference problem**: population, sample, population parameter, sample statistic, inference, statement of reliability. For a rule: the **population** is all the daily returns the rule would earn over the *immediate practical future* (a finite horizon over which a useful rule's profitability is assumed to persist even though markets are non-stationary); the **sample** is the single back test; the **parameter** is expected return (the book uses annualised average daily return on detrended data; Sharpe, profit factor etc. are alternatives); the **statistic** is the observed average return. Without some persistence of predictive power, all TA is pointless. | What exactly is being inferred. | 186–189 |
| C5 | **Sampling distribution** of a statistic: the distribution of its values over all possible samples; its **dispersion quantifies the uncertainty**; we have only one sample, so it must be estimated. Facts for the sample mean: larger samples are closer to the population mean (Law of Large Numbers); dispersion falls with `√n` (10× the sample → 3.16× narrower); more variation in the data widens it; shape tends to normal (Central Limit Theorem), with convergence depending on the parent shape (5 observations suffice in some cases, 30 in the worst shown case); ratios can be profoundly non-normal. | Uncertainty from sample size. | 202–213 |
| C6 | **Standard error of the mean** = `σ̂ / √n`, with `σ̂` estimated from the sample using divisor `n − 1`. Combined with normality, gives the classical sampling distribution. Drawback: it assumes a normal shape; if wrong, conclusions are inaccurate. | Classical test. | 213–215 |
| C7 | **Computer-intensive alternative**: resample the single sample many times to approximate the sampling distribution: **bootstrap** and **Monte Carlo permutation** (next chapter); used in the case study to build the sampling distribution of a *non-predictive rule's* average return as the benchmark. Confidence intervals come from the same distribution. | Distribution-free inference. | 215–216 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Null hypothesis / p-value | ❌ | Not produced anywhere (consistent with book 2 ch. 1 O1). |
| Standard error, t-statistic, confidence interval of mean return | ❌ | `Metrics` has none. |
| Sample size visible with every statistic | ⚠️ | `round_trips` and `fills` are shown; the number of return observations (bars) is not part of `Metrics`. |
| Best-of-N correction | ❌ | Sweeps rank by raw result; `MAX_SWEEP_RUNS` limits the grid but no adjustment (book 1 ch. 3 O7). |
| Definition of the "immediate practical future" | ❌ | No statement of the horizon over which a result is expected to hold; train/test is chronological only. |
| Resampling (bootstrap/permutation) | ❌ | Not implemented (see book 3 ch. 3 O1; ch. 5 for the methods). |
| Detrended expected return of the null | ❌ | Not implemented (book 3 ch. 1 O1). |

## 3. Opportunities

### O1 — Mean per-bar return with standard error, t-statistic and confidence interval *(book: C5, C6, pp. 209–215)*
* **Problem:** a net PnL is shown without its uncertainty.
* **Proposal:** from the equity curve compute per-bar (or per-trade) returns `r_t`, their count `n`, mean, sample standard deviation with `n − 1`, **standard error `s/√n`**, and the t-statistic `mean/SE` plus an approximate confidence interval. Report `n` beside them, and a flag when `n` is below a minimum.
* **Benefit:** puts a direct uncertainty on the headline number; the same arithmetic as the daily-Sharpe significance in book 2 ch. 1 (`Sharpe × √n`). **Complexity:** low.
* **Risks (our adaptation, not discussed in this chapter):** the classical formula assumes independent observations and the CLT shape; equity-curve returns of a strategy that holds positions are positively autocorrelated, and bars where the strategy is flat are zeros, which understates `s` and overstates the t-statistic; crypto returns are fat-tailed. Present the classical figures as optimistic and prefer the resampling versions (O2). Use **per-trade** returns as a second view because they are closer to independent.
* **Validation:** hand-computed series; zero-variance → `None`; compare against the bootstrap interval on known data.

### O2 — Bootstrap and permutation inference (distribution-free) *(book: C7, pp. 215–216; methods continue in ch. 5)*
Use resampling to build the null sampling distribution instead of assuming normality. Implementation detail belongs to the next chapter's report; cross-references: placebo/shuffled-return runner (book 3 ch. 3 O1), random-entry test (book 2 ch. 1 O1). **Complexity:** medium. Do once.

### O3 — Make the inference target explicit: horizon and parameter *(book: C4, pp. 186–189)*
State in each result what is being inferred: the expected return of this rule on this symbol/timeframe over a stated forward horizon (for example "the next N days"), measured by a named statistic (net return on detrended data or Sharpe). Pair with the pre-registration idea (book 3 ch. 2 O3). **Complexity:** low (labels and fields). It also documents the assumption of persistence (no persistence → no TA).

### O4 — Best-of-N awareness in sweeps *(book: C3, pp. 171–172)*
Show, next to the best sweep result, the **distribution of the best result under the null** (via the permutation/bootstrap of O2) so that the winner is judged against "best of N random rules" rather than a single rule. This is the data-mining correction in outline; Chapter 6 supplies the method. Cross-reference only. **Complexity:** medium (depends on O2).

### O5 — Minimum sample sizes in the UI *(book: C5, pp. 209–213)*
Display `n` (bars and trades) with every statistic and warn when it is too small for the CLT assumption the book itself places at 30 in its worst case. Extends book 1 ch. 3 O6 and book 2 ch. 6 O4. **Complexity:** very low.

### Not applicable
Textbook coin-toss and bead experiments; descriptive statistics tutorials.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O5 sample size display | medium | – | – | very low | – |
| 2 | O1 SE / t-stat / CI (with caveats) | high | – | – | low | returns series |
| 3 | O3 explicit inference target | medium | – | – | low | – |
| 4 | O2 resampling inference | **high** | – | – | medium | engine reuse |
| 5 | O4 best-of-N reference | high | – | – | medium | O2, book 3 ch. 6 |

## 5. Affected files
`analytics/domain/metrics.py` and a new `analytics/domain/inference.py` (pure functions), `backtesting/application/service.py` and sweep schemas, `docs/openapi.json`, app backtest detail and sweep pages, tests.

## 6. Incremental plan
1. Show `n` everywhere (bars, trades).
2. Pure functions for mean, SE, t, CI with per-bar and per-trade variants; unit tests.
3. Resampling inference (with ch. 5), then best-of-N reference (with ch. 6).

## 7. Acceptance criteria and tests
* `SE = s/√n` with divisor `n−1` reproduced on hand-computed series; width of the CI shrinks with `√n` in a simulation.
* Statistics return `None` with a reason for too few observations.
* No change to trading behaviour; ruff, mypy, existing tests green.
* UI text states that a p-value is the probability of the evidence under the null, not of the hypothesis (p. 169).

## Caveats
The chapter explains concepts and defers the test procedures to Chapters 5 and 6. The classical formula's independence and normality assumptions are known to be questionable for strategy returns; treat figures from O1 as lower bounds on uncertainty.
