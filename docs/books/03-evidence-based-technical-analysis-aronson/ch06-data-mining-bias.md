# Book 3 · Chapter 6 — Data-Mining Bias: The Fool's Gold of Objective TA

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 255–293 and 318–330 were read in full. The artificial-trading-rule (ATR) simulation results in pp. 294–317 (curves of bias against each factor) were read only through their summary on pp. 318–320, which restates the conclusions; individual figures were not examined. This chapter is the most relevant one in the book for the sweep feature.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Data mining is a multiple-comparison procedure**: a problem, a universe of candidate rules, a figure of merit; the best observed performer is selected. The selected rule is the one most likely to do best in future (proved by White as observations grow), **but its observed performance is a positively biased estimate of its expected performance**. Anecdotes (monkeys, Bible codes, Bangladesh butter with correlation 0.70 across hundreds of series) illustrate that the rare is likely after the fact. | Why the winner disappoints. | 255–264, 281–282 |
| C2 | **Definitions**: data-mining bias = expected difference between the best rule's observed and expected performance; rule universe and universe size; in-sample vs out-of-sample. Search types: **parameter optimisation** (narrowest), **rule searching** (different forms), **rule induction** (variable complexity; machine learning). All suffer the bias. | Scope of the problem. | 255–256, 264–267 |
| C3 | **Single-rule back test**: observed mean is an *unbiased* estimate. **Data mining**: observed performance is a *selection criterion*; using it also as an estimate is "the data miner's mistake". Out-of-sample deterioration is mostly regression from a lucky selection, not necessarily a change in the market. | Two different roles of the same number. | 268–272, 262–264 |
| C4 | **Mean vs maximum**: the data miner observes the *maximum mean among N means*; the right null distribution is that of the maximum of N, centred above zero (for 50 useless rules the maximum-mean sampling distribution is centred at +33%, so an observed +37% had p ≈ 0.45 instead of < 0.05). | Using the wrong sampling distribution. | 275–278 |
| C5 | **Two causes of the bias**: randomness + the selection imperative. **The more luck relative to merit (typical of markets), the larger the bias.** | Why markets are the worst case. | 278–284 |
| C6 | **Five factors** set the bias (for the mean-return statistic): (1) **number of rules tested** (bias grows with the log of N), (2) **number of observations** (more observations → less bias), (3) **correlation among rule returns** (more correlated → lower bias, because the effective number of rules shrinks), (4) **positive outliers** (large outliers raise it, diluted by more observations), (5) **variation in true merit** among the rules (similar merit → larger bias). Statement of where experiments agree: data mining works when the sample is large; fails when too small. Relationships are for the mean; other statistics (Sharpe) may behave differently. | Predicting how bad it is. | 287–291, 318–320 |
| C7 | **Solutions**: (a) **out-of-sample testing** (unbiased, but the data's "virginal status" is lost once used; reduces data for mining; arbitrary partition; schemes: early/late split, checkerboard, **walk-forward** with moving windows whose test segments do not overlap, giving independent estimates and a confidence interval); (b) **Markowitz–Xu correction** (shrink best performance toward the mean of all rules: `H' = R + B(H − R)`, needs all rules' interval returns; "can work surprisingly well, but can also fail miserably"; use as rough guideline); (c) **randomisation** that tests the best of N. | Dealing with the bias. | 320–324 |
| C8 | **White's Reality Check (bootstrap)**: the full set of interval returns of every rule tested; resample dates with replacement (same count as the sample, same dates for all rules); subtract each rule's own mean (zero-centre); take the **maximum mean** across rules per resample; repeat ≥ 500 times; p-value = share of maxima ≥ the observed best. **Patented** (Halbert White; software from Quantmetrics). **Monte Carlo permutation (MC, Masters)**: keep each rule's output series; pair with the *same* scrambled market changes across all rules (to preserve the correlation among rules); take the maximum mean; repeat; no zero-centering needed; cannot give confidence intervals; the enhanced version (Romano & Wolf) will be placed in the public domain (author's statement). Both lose power if the universe contains rules **worse than useless** (Hansen), e.g. inverse rules. | The correct best-of-N test. | 324–330 |
| C9 | Practical requirement: **retain the interval returns (or outputs) of every rule tested**; "few data miners save this information". | Prerequisite data. | 327 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| A rule universe exists | ✅ | Sweeps queue one backtest per parameter combination over the same candles (`BacktestService.create_sweep`), up to `MAX_SWEEP_RUNS`; strategy parameter grids are explicit. |
| Selection by best observed performance | ✅ and **unchecked** | The sweep UI/API lists run metrics; the operator picks the best. Nothing corrects the bias or says it exists. |
| Retaining each rule's per-bar returns/positions | ⚠️ | Each run stores its `equity_curve` and `fills` (via the backtesting repository), so per-bar returns can be recomputed; positions are not stored as a series (derivable from fills). Skipped/invalid combinations are stored in the sweep's `skipped` list. |
| Universe size across the whole research history | ❌ | Not tracked across sweeps, manual runs, other strategies or pairs. The true N is larger than any single sweep. |
| Correlation among rules / effective N | ❌ | Not computed. |
| Out-of-sample | ⚠️ | One chronological split per run; each sweep run can be judged on the same test part, so the test segment is **reused** by every selection (its "virginal" status is lost). |
| Walk-forward with independent test folds | ❌ | None. |
| Markowitz–Xu / randomisation | ❌ | None. |
| Parameter count per strategy | ✅ low | 2–4 parameters each. |

## 3. Opportunities

### O1 — Best-of-N Monte Carlo permutation test for sweeps *(book: C8, pp. 327–330; builds on book 3 ch. 5 O1)*
* **Problem:** a sweep's best configuration is reported with its raw result, which the book says is biased upward and whose single-test p-value is invalid (p ≈ 0.45 rather than < 0.05 in the 50-rule example).
* **Proposal:** for a completed sweep, take the per-bar **position series of every run** (aligned on the same candle index), draw `M` random permutations of the detrended bar returns **using the same permutation for all runs** (the book stresses this to preserve the correlation structure), compute each run's mean net return under that pairing, record the **maximum across runs**, and report the p-value of the observed best run against that distribution. Add the sweep-level null distribution (median, 95th percentile) so the UI can show "what the best of N useless rules would typically earn".
* **Benefit:** a defensible answer to "is the winner more than luck?"; discourages picking the top of a grid. It needs no strategy re-execution.
* **Complexity:** medium: depends on storing/deriving per-bar position series per run, a batched numerical routine, and a job for large sweeps.
* **Risks:** (a) as in ch. 5 O1, permuting returns destroys volatility clustering and autocorrelation; (b) the book notes reduced **power** when the universe contains rules worse than useless (inverse rules in the book; for us, parameter combinations that are clearly bad) — consider restricting the universe to configurations that are plausible a priori (documented before running, see O2) rather than adding junk; (c) it addresses one sweep, not the full history of tries (O2); (d) a p-value from M = 500–5,000 permutations has resolution 1/M; (e) the enhanced (Romano–Wolf) version is described by the author as available on a website (evidencebasedta.com), not in the book: the basic MC version is the baseline.
* **Method status:** the author calls MC **public domain** and White's Reality Check **patented**. Implement the permutation method; do not implement WRC without a legal check by the owner.
* **Validation:** a sweep of random rules must yield p roughly uniform; one planted truly profitable rule among noise must be detected; with N = 1 it must reduce to the single-rule test of ch. 5; identical pairings across runs (test by correlated duplicate runs, which must not inflate the maximum).

### O2 — Universe accounting: count every configuration ever tried *(book: C1, C4, C6, pp. 255–256, 275–278, 287–288)*
* **Problem:** N is the multiplier of the bias; hidden N (earlier sweeps, manual runs, other strategies, other pairs, other timeframes) is the usual way to fool oneself.
* **Proposal:** record each backtest/sweep configuration in a **research universe** keyed by (exchange, symbol, timeframe, data window, strategy family) and show the cumulative count of distinct configurations tried on the same data next to any result, with the sweep-level N used by O1 as the lower bound. Extends book 2 ch. 1 O5 and book 1 ch. 3 O7. Allow the operator to define the universe explicitly (a named "study") before running, as pre-registration (book 3 ch. 2 O3).
* **Complexity:** low–medium. **Risk:** the count can still be gamed by deleting runs; make deletion audited. **Validation:** API test that counts are monotonic.

### O3 — Stop presenting the winner's raw metric as an estimate *(book: C3, pp. 270–272)*
* **Proposal:** in sweep views, label the top result "selection result (biased upward)" and show instead (a) the median result across the grid, (b) the best-of-N null from O1, and (c) the test-segment result **only for the single selected configuration**, flagged as consumed once looked at. **Complexity:** very low (copy and layout). Include a one-line explanation of data-mining bias.

### O4 — Effective number of independent rules *(book: C6 factor 3, pp. 288, 318 · computation is our adaptation)*
* **Proposal:** compute the pairwise correlation of per-bar returns among sweep runs and report an *effective N* (for example from the eigenvalues of the correlation matrix). Neighbouring parameter combinations (EMA 9/21 vs 10/21) are highly correlated, so the effective N is much smaller than the grid size. The book states the direction of the effect (correlation shrinks the bias) but gives no formula for effective N; the formula is ours and is only a descriptor. **Complexity:** low–medium. **Validation:** duplicates give effective N ≈ 1; independent noise gives ≈ N.

### O5 — Non-overlapping walk-forward folds with an interval *(book: C7, pp. 322–323)*
Already recorded as B-WALK-FORWARD (book 1 ch. 3 O8, book 2 ch. 1 O2). This chapter adds the specification: moving window split into train and test, test segments **non-overlapping** across folds so their performance estimates are independent, a confidence interval from the dispersion of the fold results, and the caveats that each held-out segment is used up by selection. Pairs naturally with Aronson's O1 (best-of-N inside each training fold). **Complexity:** high; plan after O1–O3.

### O6 — Keep per-bar data for every sweep run *(book: C9, p. 327)*
Prerequisite for O1/O4: store, for each run, a compact per-bar array (position and net return) or guarantee that it can be recomputed deterministically from candles + config (the existing `seed` and candle hash help). Storage cost must be bounded (for example arrays of small numbers, compressed). **Complexity:** low–medium.

### O7 — Markowitz–Xu shrinkage as an optional rough guide *(book: C7, pp. 323–324)*
The book itself calls the method approximate and sometimes badly wrong and does not give the shrinkage factor formula (it refers to De La Maza). Defer; consider only if the formula is obtained from the cited source and validated on synthetic universes. **Complexity:** medium; low priority.

### Not applicable
Bible Codes and anecdotal sections; rule induction and machine learning (book 5 covers).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 label/explain winner bias | high | – | – | very low | – |
| 2 | O2 universe accounting | high | – | – | low–medium | – |
| 3 | O6 per-bar data retention | – | – | medium | low–medium | – |
| 4 | O1 best-of-N MC permutation | **high** | – | – | medium | O6, book 3 ch. 5 O1 |
| 5 | O4 effective N | medium | – | – | low–medium | O6 |
| 6 | O5 walk-forward | high | – | – | high | O1 |
| 7 | O7 Markowitz–Xu | low | – | – | medium | source formula |

## 5. Affected files
`backtesting/application/service.py` (sweep post-processing job), `backtesting/domain/` (permutation best-of-N, per-bar series), `backtesting/infrastructure/orm.py` and repository (universe records, compact arrays), `analytics/domain/`, `docs/openapi.json`, app sweep pages (`routes/backtests/sweeps/$sweepId`), tests (`api/tests/unit`, integration).

## 6. Incremental plan
1. Copy and layout: label the winner as biased (O3).
2. Universe accounting (O2).
3. Retain or recompute per-bar arrays for sweep runs (O6).
4. Single-rule permutation test (book 3 ch. 5 O1), then best-of-N across a sweep (O1) with a shared permutation.
5. Effective N descriptor (O4).
6. Walk-forward after the above.

## 7. Acceptance criteria and tests
* On a sweep of random-position rules the best-of-N p-value is approximately uniform; with one planted effect it is detected.
* The shared permutation is used for all runs (assert identical pairings in a unit test).
* The reported best observed return is never shown without the best-of-N reference and N.
* No change to trading behaviour; existing runs and API stay compatible; ruff, mypy and tests green.
* The licensing status of the method used is recorded in `docs/` before release.

## Caveats
The experiments in the chapter use artificial rules on monthly S&P 500 data and describe the *mean-return* statistic; the dependence on the five factors may differ for Sharpe or drawdown-based ranking. Passing the best-of-N test is evidence about *this sample*, not a promise about the future, and the test says nothing about the unknown number of tries made outside the recorded universe.
