# Book 3 · Chapter 5 — Hypothesis Tests and Confidence Intervals

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 217–253 was read.

## 1. Chapter summary (pp. 217–253)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Two inference procedures: **hypothesis tests** (is an effect present?) and **estimation** (how large? point estimate and **interval estimate**). Informal inference is biased toward confirmatory evidence; confirmatory evidence is *necessary but not sufficient* (affirming the consequent); the hypothesis test is built on **denial of the consequent**. | Why "it worked in the backtest" is not enough. | 217–219 |
| C2 | **Hypotheses**: `H_A` the rule's expected return > 0 (on detrended data); `H₀` it is ≤ 0. Mutually exclusive and exhaustive; the test targets `H₀` because it reduces to one claim (return = 0; a rejection of 0 contradicts all lower values). `H₀` is assumed true for **skepticism** (burden of proof on the claimant, like presumption of innocence) and **simplicity** (Occam: fewer parameters fit by chance less; a 10-coefficient polynomial fits any 10 points). **Rejecting `H₀` is a strong decision; retaining it is weak** (absence of evidence ≠ rule is useless). | Logic of the test. | 220–227 |
| C3 | **Mechanics**: hypothesis, test statistic (the rule's mean return), sampling distribution under `H₀` (centred at zero). **p-value** = conditional probability, under `H₀`, of a statistic at least as large as observed = share of the sampling distribution's area at or beyond it; threshold chosen **before** the test. Scale: 0.10 possibly significant, **0.05** statistically significant, 0.01 very, 0.001 highly. The p-value is *not* the probability that `H₀` is true. | Quantifying "surprising". | 227–233 |
| C4 | **Errors**: type I (reject a true `H₀`: trade a worthless rule) vs type II (miss a good rule). For a trader **type I is worse** (lost capital vs lost opportunity). | Cost of being wrong. | 233–234 |
| C5 | **Computer-intensive sampling distributions**. *Bootstrap*: tests `H₀: expected return ≤ 0`; steps: compute the rule's mean daily return on detrended data; **zero-centre** the rule's daily returns (subtract their mean); resample **with replacement exactly N times** (N = original sample size) 5,000 times; the share of resampled means ≥ the observed mean is the p-value. *Monte Carlo permutation (MCP, Masters)*: tests `H₀: the rule's outputs are randomly paired with market changes`; keeps the rule's output sequence in order and pairs it, **without replacement**, with randomly permuted detrended one-day-forward market changes; average the products; repeat 5,000 times; p-value = share ≥ observed. They test slightly different nulls; agree generally on detrended data. The **MCP is public domain; the bootstrap variant suitable for data-mined rules (White's Reality Check) is patented** according to the author (pp. 235–236). | How to get the null distribution. | 234–243 |
| C6 | **Worked example** (rule TT-4-91, 91-day channel breakout on the Dow Jones Transportation Index, trading the S&P 500, Nov 1980–Jun 2005, 6,800 observations): +4.84%/yr on detrended data; bootstrap p = 0.0692 ("possibly significant"); MCP gave almost the same. The p-value assumes this was the *only* rule tried. | Application. | 240–243 |
| C7 | **Estimation**: the sample mean is an unbiased, consistent, efficient and sufficient estimator of the population mean (for symmetric populations; its standard error is smaller than the median's). **Confidence interval**: derived from the same sampling distribution, centred at the sample mean; a 90% interval covers the true value in about 90% of independent samples; higher confidence = wider interval. **Bootstrap percentile method**: sort the resampled means and trim `(100 − level)/2 %` from each end. **MCP cannot produce confidence intervals** (it tests information content, not a parameter). Example: 80% CI for TT-4-91 = +0.62% to +9.06%. | Size of the effect. | 243–253 |
| C8 | Test and interval may disagree when the sampling distribution is skewed; the Central Limit Theorem makes the **mean** a good statistic with large samples; other statistics (ratios) may need pivoted bootstrap methods. | Choice of statistic. | 250–252 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| `H₀`, p-value, significance labels | ❌ | None in `analytics` or the backtest API. |
| Bootstrap / permutation machinery | ❌ | No resampling code anywhere in `api/src`. |
| Confidence intervals of mean return | ❌ | Not computed. |
| Preconditions available | ⚠️ | The engine yields an equity curve (per-candle) and fills; a per-candle **position state** (flat/long) exists inside the loop (`quantity`) but is not returned in `BacktestOutcome` (`models.py`). Per-bar returns can be derived from the equity curve. The `seed` field on `BacktestConfig` already exists for reproducibility. |
| Error costs asymmetry | ✅ conceptually | Live promotion requires paper days, caps and approvals, i.e. the system is already biased against type I errors; nothing ties it to evidence. |
| Licensing of methods | n/a | No code yet. |

## 3. Opportunities

### O1 — Monte Carlo permutation test on a backtest's position series *(book: C5, pp. 238–243 · long/flat form is our adaptation)*
* **Problem:** no probabilistic statement can be attached to a result.
* **Proposal:** a pure function `permutation_test(position, bar_returns, n=5000, seed)` that keeps the strategy's per-bar position series (1 when in the market, 0 otherwise; the book's ±1 generalises) in its original order, pairs it without replacement with random permutations of the (detrended) bar returns, averages the position-weighted returns, and returns the p-value. Position series is exactly what the book calls the rule's output. Return the full null distribution summary (mean, quantiles) so the UI can draw it.
* **Key advantage for us:** it needs **no re-run of the strategy**: only arrays, so it is cheap and deterministic with `seed`. It also encodes the exposure-adjusted benchmark of book 3 ch. 1 (the null automatically has the same time in the market).
* **Benefit:** a defensible p-value per backtest and per train/test segment; the sweep can show a p-value per cell (but see book 3 ch. 6 for the multiplicity correction).
* **Complexity:** low–medium: `BacktestOutcome` must carry the per-bar position (additive); detrending uses the sample mean of bar returns (book 3 ch. 1); sorting for percentile; runtime O(5,000 × bars) is fine.
* **Risks:** (a) the permutation destroys autocorrelation in market returns, which is the null the book intends but which can make breakout strategies look better than under a volatility-clustered null; (b) with costs, the permuted null should include the trading costs implied by the *original* trade pattern (the position series is unchanged, so costs are the same) and the p-value should be on net returns; (c) the book's examples use ±1 positions and daily data; flat periods and 24/7 intraday bars change the distribution of the statistic; (d) dependence of position on past returns (a trend rule is always long after rises) is exactly what is being tested, so the test is valid, but a few long position runs mean few effective degrees of freedom: report the number of position runs next to the p-value.
* **Validation:** a position series built from the *future* returns (cheating) must give p≈0; a random series gives uniform p; the book's expected-return formula check (book 3 ch. 1 O1); same seed → same result.

### O2 — Zero-centred bootstrap p-value and percentile confidence interval for mean return *(book: C5, C7, pp. 235–238, 248–250)*
* **Proposal:** resample the strategy's per-bar (or, better for dependence, per-trade or **block**) returns with replacement, N draws per resample, 5,000 resamples: (a) zero-centre for the p-value; (b) do not centre for the percentile confidence interval; present both with the sample size. Block resampling is our adaptation for serially dependent returns; the book's version resamples individual daily returns.
* **Benefit:** a confidence interval that does not assume normality; complements O1 (test of information content vs estimate of size). **Complexity:** low–medium. **Risks:** the book's iid resampling underestimates uncertainty when returns are autocorrelated; zero-centering keeps skew and kurtosis (good) but assumes the sample is representative; the distribution of a strategy's per-bar returns is spiky (mostly zeros). **Validation:** known-mean synthetic data; coverage simulation: about 90% of 90% intervals cover the true mean.

### O3 — Present results with the book's significance vocabulary and with caveats *(book: C3, C4, pp. 231–234)*
Show p-value, level label (possibly/statistically/very/highly significant) and a fixed sentence that the p-value is the probability of this result **if the strategy had no skill**, not the probability that it has skill; show whether the number of tests that led to this result is 1 or N (book 3 ch. 6). **Complexity:** very low.

### O4 — Evidence gate for live promotion (type I is worse) *(book: C4, p. 234 · adaptation)*
* Extend the live readiness checks (`bots/application/live.py`) with an optional, explicit criterion that the backtest of the bot's configuration has a permutation p-value below a threshold set by the operator **and** that the correction for the number of configurations tried (book 3 ch. 6) is applied. Off by default. Rationale: the book argues that wrongly adopting a useless rule is costlier than missing a good one. **Complexity:** low once O1 and ch. 6 exist. **Risk:** false confidence from a passed test; keep paper-days, caps and approvals unchanged.

### O5 — Licensing and method choice *(book: C5, pp. 235–236)*
The author states that the bootstrap form that handles data-mined rules (White's Reality Check) is **patented** (Halbert White; software by Quantmetrics) and that the Monte Carlo permutation method is public domain. Before implementing a data-mining correction (ch. 6), verify the legal status of whatever algorithm is chosen (this is a verification task for the owner, not legal advice from this analysis), and prefer methods whose status is clear. Plain bootstrap and permutation tests are standard statistics. **Complexity:** none for code; a decision.

### Not applicable
Textbook estimator properties, tennis analogy, bead experiments.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 permutation test | **high** | – | – | low–medium | per-bar position in `BacktestOutcome` |
| 2 | O3 vocabulary and caveats | medium | – | – | very low | O1 |
| 3 | O2 bootstrap p and CI | high | – | – | low–medium | – |
| 4 | O5 licensing check | – | – | – | none | before ch. 6 work |
| 5 | O4 evidence gate | – | medium | medium | low | O1, ch. 6 |

## 5. Affected files
`backtesting/domain/models.py` (position series in `BacktestOutcome`), `backtesting/domain/engine.py` (emit it), new `analytics/domain/inference.py` (permutation, bootstrap), `backtesting/application/service.py` and `router.py` (result fields), `docs/openapi.json`, `bots/application/live.py` (O4), app backtest detail and sweep pages, tests.

## 6. Incremental plan
1. Carry per-bar position in the outcome (additive; hash and stored runs unaffected).
2. Pure permutation and bootstrap functions with synthetic tests.
3. Expose p-value and interval as optional result fields for the whole run and each segment.
4. UI: distribution plot and labelled p-value; wording per O3.
5. Later: the multiplicity correction (ch. 6) and optional promotion gate.

## 7. Acceptance criteria and tests
* A strategy with deliberate look-ahead (positions from future returns) gets p near 0; an alternating random position gets p roughly uniform over many seeds.
* The bootstrap interval covers the true mean about the nominal fraction in simulation.
* Determinism: same seed and inputs → identical p-value.
* Runtime for 5,000 permutations on typical runs stays within an agreed budget; computation can be asynchronous like other jobs.
* No change to trading or to stored results unless the optional fields are requested; ruff, mypy, existing tests green.

## Caveats
All p-values are conditional on `H₀`, on the chosen statistic and on a single test (p. 242). The case-study rule was "possibly significant" at p = 0.069, i.e. not significant at 0.05, and that was before accounting for the thousands of rules tried (next chapter). Significance on past data does not imply future profit.
