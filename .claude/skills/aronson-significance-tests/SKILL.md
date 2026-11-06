---
name: aronson-significance-tests
description: Hypothesis testing and confidence intervals for trading-rule returns, from David Aronson's "Evidence-Based Technical Analysis" ch. 4-5 — sampling distribution, standard error, p-values, type I vs type II errors, bootstrap and Monte Carlo permutation (MCP) procedures step by step, confidence intervals, and practical vs statistical significance. Use when you need to test whether a single backtested rule's average return is distinguishable from luck, or to build a bootstrap/permutation test for the bots' backtests.
---

# Significance tests for rule returns (Aronson, *Evidence-Based Technical Analysis*, ch. 4-5)

Page numbers are book pages. **[Adaptation]** = ours, not the book's (it tests daily S&P 500 rules). Chapter analyses: `docs/books/03-evidence-based-technical-analysis-aronson/ch04-*.md`, `ch05-*.md`. **These tests assume you tested exactly one rule.** If you picked it from many, use `aronson-data-mining-bias` instead.

## 1. The inference problem (pp. 165-189)
Six components: population (all daily returns the rule would earn in the practical near future — a finite horizon over which usefulness is assumed to persist), sample (one backtest), parameter (expected return; the book uses annualized mean daily return on detrended data; Sharpe or profit factor are alternatives), sample statistic (observed mean), inference, and a statement of reliability. Without some persistence of predictive power, technical analysis makes no sense.
Null hypothesis `H0`: expected return <= 0 on detrended data. `HA`: > 0. A profitable backtest is "luck" until shown otherwise.

## 2. Sampling distribution (pp. 202-215)
- Distribution of the statistic across all possible samples; its **spread quantifies uncertainty**.
- Law of large numbers; spread shrinks with `sqrt(n)` (10x more data -> 3.16x narrower); more variation in the data widens it; the mean tends to normal (central limit theorem) — five observations enough in some cases, 30 in the worst example; ratios can be strongly non-normal.
- **Standard error of the mean = s / sqrt(n)** with divisor n-1. It presumes a normal shape; if wrong, conclusions are wrong.

## 3. Reading the p-value (pp. 227-234)
p-value = fraction of the null sampling distribution as extreme as the observed statistic = probability of this evidence **if `H0` is true**; it is **not** the probability that `H0` is true. Set the threshold **before** testing. Scale used: 0.10 possibly significant, **0.05 significant**, 0.01 very significant, 0.001 highly significant.
Rejecting `H0` is a strong decision; **not** rejecting is weak (absence of evidence is not proof of uselessness) (pp. 220-227). Type I (trading a useless rule) is worse for a trader than type II (missing a good one) (pp. 233-234). Skepticism and Occam: the proponent carries the burden of proof; fewer parameters fit noise less easily (a degree-10 polynomial fits any ten points).

## 4. Computer-intensive null distributions (pp. 234-243)
Both use **detrended** daily returns of the market.
**Bootstrap** (tests `H0: expected return <= 0`):
1. Compute the rule's mean daily return on detrended data.
2. Center the daily rule returns at zero (subtract their mean).
3. Resample **with replacement** N times (N = original sample size), take the mean; repeat **5,000** times.
4. p-value = fraction of resampled means >= the observed mean.
**Monte Carlo permutation (MCP, Masters)** (tests that rule outputs are randomly paired with market changes):
1. Keep the rule's signal sequence; reorder the detrended future market changes **without replacement**.
2. Pair signals with the shuffled changes, compute the mean of the products.
3. Repeat 5,000 times; p-value = fraction >= observed.
They test slightly different nulls but usually agree on detrended data. MCP is public domain; White's Reality Check (bootstrap for mined rules) is patented (pp. 235-236 per the author).
Worked example: rule TT-4-91 (91-day channel breakout on Dow Transports, trading the S&P 500, Nov 1980 - Jun 2005, 6,800 observations): +4.84%/yr detrended, bootstrap p = 0.0692 ("possibly significant"), MCP nearly equal — and that p assumes it was the **only** rule tested (pp. 240-243).

## 5. Estimation and confidence intervals (pp. 243-253)
Sample mean is an unbiased, consistent, efficient, sufficient estimator (symmetric populations). The CI comes from the same sampling distribution: bootstrap percentile — sort resampled means and trim `(100 - level)/2 %` from each end. A 90% CI covers the true value in ~90% of independent samples; higher confidence = wider. **MCP gives no CI** (it tests information content, not a parameter). Example: 80% CI for TT-4-91 = +0.62% to +9.06%. Tests and intervals can disagree for skewed distributions; the mean is a good statistic for large samples while ratios may need pivoted bootstrap (pp. 250-252).

## 6. Statistical vs practical significance (pp. 391-394)
With >6,000 observations a trivial edge can be significant. Fix an economic threshold in advance (e.g. a required expected return after costs).

## 7. [Adaptation] Implementation notes for the bots
- Compute on **per-bar detrended returns net of fees/funding** for the rule's actual positions; keep serial correlation in mind (the plain bootstrap assumes independent days — consider a block bootstrap for autocorrelated bar returns and report the block size).
- Use 5,000+ resamples with a fixed seed so results are reproducible; store seed, N, p-value, CI and the statistic.
- Report both bootstrap and permutation p-values and the number of rules that were looked at (`trials`) beside them.
- Intraday crypto bars are highly dependent; the number of **independent** observations is far smaller than the bar count.
- A p-value from this skill is only valid for a pre-specified single rule; otherwise correct with `aronson-data-mining-bias`.
