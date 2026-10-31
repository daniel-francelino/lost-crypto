# Book 5 · Chapter 11 — The Dangers of Backtesting

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 151–158 were read in full (including the PBO/CSCV algorithm and exercises). The bibliography was not read.

**Relevance:** the most directly applicable chapter in the book to the platform's backtesting and sweep modules: **recording every trial**, **deflating** results by the number of trials and estimating the **probability of backtest overfitting (PBO)** from a matrix of strategy P/L series. The platform already produces exactly such a matrix whenever it runs a sweep.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | "Researching and backtesting is like drinking and driving." Most published backtests are flawed by selection bias on multiple tests. A backtest is a **hypothetical, not an experiment**; it "does not prove anything" and "guarantees nothing, not even achieving that Sharpe ratio if we could travel back in time"; random draws would have been different. Its value is a **sanity check** on bet sizing, turnover, resilience to costs and behaviour in a scenario. | What a backtest is. | 151–152 |
| C2 | **Seven sins** (Luo et al., Deutsche Bank 2014): survivorship bias; **look-ahead bias** (timestamps, release dates, backfill); storytelling (ex-post story for a random pattern); **data snooping** (training on the testing set); **transaction costs** (only trading reveals the real cost); **outliers** (strategies resting on a few extreme events); shorting (borrow availability and cost). Other errors: non-standard performance computation (ch. 14), ignoring hidden risks, only looking at returns, confusing correlation with causation, **an unrepresentative period**, failing to expect the unexpected, **ignoring stop-out limits/margin calls**, ignoring funding costs, forgetting practical aspects. | Checklist of errors. | 152 |
| C3 | **Even a flawless backtest is probably wrong**: becoming an expert means having run tens of thousands of backtests, so a good result may be a fluke from multiple testing; "the better you become at it, the more likely false discoveries will pop up". | Multiple testing even with correct mechanics. | 152–153 |
| C4 | **Backtesting is not a research tool**: feature importance (ch. 8) is derived ex-ante and explains patterns; backtests give little insight on why a strategy made money; hundreds of published "alphas" are "lottery tickets that won the last game" while the millions of simulations behind them are not reported. **The purpose of a backtest is to discard bad models, not to improve them**; adjusting a model based on backtest results is "a waste of time and dangerous"; never backtest until the model is fully specified; if it fails, start over. | Role of backtests. | 153 |
| C5 | **Backtest overfitting = selection bias on multiple backtests.** Recommendations: (1) develop models for **entire asset classes/universes** rather than specific securities (a mistake found only on one security is likely a false discovery); (2) **bagging** (if it deteriorates performance, the strategy was overfit to few observations or outliers); (3) don't backtest until research is complete; (4) **record every backtest conducted on a dataset** to estimate the probability of backtest overfitting and **deflate the Sharpe ratio by the number of trials**; (5) **simulate scenarios rather than history** (history is one random path; thousands of "what if" scenarios are harder to overfit); (6) if the backtest fails start from scratch (Second Law). | Practical countermeasures. | 153–154 |
| C6 | **Strategy selection**: k-fold CV leaks (ch. 7); scikit-learn's walk-forward moves testing forward but with long-range serial dependence testing right after the training set may not avoid leakage, and "there is a single path of testing that can be repeated over and over until a false positive appears"; randomisation is needed. | Limits of walk-forward. | 155 |
| C7 | **Probability of Backtest Overfitting (PBO) via combinatorially symmetric cross-validation (CSCV)**: collect a `T × N` matrix `M` of P/L series for the `N` configurations tried (synchronous rows); split rows into `S` equal contiguous blocks (S even); for every combination of `S/2` blocks as the training set `J` (with the complement as testing set `J̄`; `S = 16` gives 12,780 combinations): compute the performance statistic `R` for each trial on `J`, pick the best `n*`, compute its **relative rank `ω_c`** among all trials on `J̄`, and the logit `λ_c = ln(ω_c/(1 − ω_c))`; the PBO is the share of combinations with `λ ≤ 0` (the in-sample best trial performs at or below the median out-of-sample). Example: best SR in-sample vs out-of-sample shows decay `SR_OOS = 0.87 + 0.75·SR_IS`, adj. R² 0.17, `Prob[SR_OOS < 0] = 0.74`, **PBO = 0.74**. Blocks keep their time order; the random sampling is on weakly dependent subsets. | A quantitative overfitting probability from the sweep itself. | 155–157 |
| C8 | Exercises: seasonally adjusted data aligned with the wrong month (look-ahead); signals from closing prices executed at the close (look-ahead); spurious correlations; the "September effect" (data snooping/storytelling); P/E ranking performance (survivorship/look-ahead). | Spot the sin. | 158 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Next-bar execution (no signal-and-fill on the same close) | ✅ | The engine fills at the next candle open (`engine.py`); exercise 11.2 (close-signal executed at close) is avoided by design. |
| Costs always applied | ✅ | `fee_rate`, `slippage_bps`. |
| Survivorship bias | ⚠️ | Choosing today's top pairs/tokens means survivors only (delisted or collapsed tokens are absent); the platform trades pairs the user selects (mostly majors). |
| Multiple testing accounting | ❌ | No trial counter, no deflated Sharpe, no PBO. |
| Sweep outputs as a trial matrix | ⚠️ | Sweep runs produce results per configuration; the per-period P/L (equity or returns) series are available from each backtest (verify what is persisted: equity curve per run?). PBO needs synchronous P/L series for all configurations. |
| Scenario simulation (vs one historical path) | ❌ | Single historical path; synthetic or resampled scenarios absent (ch. 12–13). |
| Backtest as discard tool, not as optimiser | ❌ | UI encourages "best result" selection; no locked evaluation. |
| Outlier dependence check | ❌ | See book 4 ch. 21 O1/O5 (top-N trades, shocks). |
| Margin calls / stop-out | n/a | Spot long-only without leverage. |
| Representativeness of the period | ❌ | No regime labelling or coverage statement (bull/bear/sideways share of the sample). |

## 3. Opportunities

### O1 — Trial ledger: record every backtest and sweep member per dataset and strategy family *(book: C5 item 4, p. 154)*
Same as book 5 ch. 1 O3 and ch. 8 O1 and book 4 ch. 21 O2; make it a first-class table (`trials`: dataset hash/asset/timeframe/range, strategy family, parameters, metrics, created_at, `research_or_evaluation` flag), populated automatically by every backtest and sweep run (including discarded and failed-quality ones). It is the denominator for all deflation (O2, O3). **Complexity:** low–medium (migration + service hook). **Risks:** counting runs of identical parameters repeatedly (de-duplicate by configuration hash but also keep the raw count); users on separate datasets create separate ledgers (by design: the book's trials are per dataset). **Validation:** each execution creates exactly one entry; sweep creates N entries; duplicates counted once in the "effective trials" figure and tracked in raw count.

### O2 — PBO (CSCV) report for every sweep *(book: C7, pp. 155–157)*
* **Proposal:** implement the CSCV algorithm as a pure function over a `T × N` matrix of per-period returns (use daily or timeframe returns of each configuration's equity curve, aligned on the same index; choose `S` by default 8–16, S = 16 for 12,780 combinations; limit combinations by sampling if too many), producing: the **logit distribution**, the **PBO**, the **IS vs OOS performance degradation regression** (slope, intercept, R², probability that the OOS metric of the IS-best is negative), and the **rank of the selected configuration**. Display with the sweep: "Probability of backtest overfitting: 74%" with an explanation and a plot. Uses Sharpe or Sortino or net return as the statistic (the statistic must be computable on subsets).
* **Why:** this is the one tool in the book that turns the platform's existing sweep (the strongest source of selection bias) into a quantitative warning; it needs no new data. It also resolves the question that book 4 ch. 21 raised qualitatively ("is the best result robust?").
* **Complexity:** medium (combinatorics; vectorised implementation; storage of per-run return series). **Risks:** requires enough observations per block (T/S) for the statistic to be meaningful; assumes performance within blocks is approximately iid for Sharpe subsamples; trials that are near duplicates (adjacent parameters) are highly correlated, which changes the interpretation (PBO is low if the best region is a broad plateau—consistent with robustness) and does not account for trials run before the sweep (the ledger tracks those); long-memory strategies with few trades have zero-return blocks. **Validation:** (a) a sweep of pure noise strategies (random walk data) yields PBO near 0.5 or higher; (b) a planted real edge yields low PBO; (c) invariance to column permutation; (d) deterministic with a fixed combination set; (e) matches published example values on a small hand-built matrix.

### O3 — Deflate the headline result by the number of trials (deflated Sharpe, ch. 14) *(book: C5 item 4, p. 154)*
Show next to the best sweep result the *probability that its Sharpe is genuine given N trials* (the deflated Sharpe ratio, chapter 14 O1), using the ledger count. Without it, "best of 200" is reported as if it was a single test. **Complexity:** low once ch. 14 formulas exist.

### O4 — "Backtest is a discard tool": split the product flow into Research (exploratory, results labelled non-evidence) and Evaluation (locked, run-once) *(book: C4, C5, pp. 153–154)*
The same recommendation as ch. 1 O4, book 3 ch. 6 O5 and book 4 ch. 21 O3; here the book's rationale: adjusting the model after seeing a backtest is dangerous. Product changes: label exploratory runs "exploratory — not evidence" in the UI, display the ledger count, and require an **evaluation run** (frozen configuration and data range, one shot) before a bot can be promoted to paper (ch. 1 O1 gates). **Complexity:** medium.

### O5 — Backtest sanity-check list in the UI (the seven sins + crypto-specific items) *(book: C2, p. 152)*
A short checklist shown with every backtest result: look-ahead (next-open fills ✔), costs (✔ fee/slippage with values), survivorship (⚠ asset selection), outliers (top trades share, shocks), period representativeness (share of time in each regime; first/last data dates), liquidity (volume cap), data quality (candle validator report; book 4 ch. 22 O1). Crypto-specific adaptation (ours): exchange downtime and delistings (survivorship), stablecoin depegs, funding costs for perpetuals (not applicable to spot), maker/taker fee tiers. **Complexity:** low–medium (aggregates already planned elsewhere).

### O6 — Universe-level checks: require a result on more than one asset before treating a parameter set as a finding *(book: C5 item 1, p. 154)*
Same as book 4 ch. 21 O10. The book's rule: a mistake found only on one security is likely a false discovery. Caveat: crypto correlations are high, so passing on BTC and ETH is weaker evidence than for unrelated assets. **Complexity:** medium.

### O7 — Scenario-based evaluation instead of a single path *(book: C5 item 5, p. 154 → chapters 12–13)*
Defer detail to chapters 12 and 13 (combinatorial purged CV, synthetic data). Placeholder here to keep the chain: PBO (O2) uses recombinations of the historical blocks; synthetic scenarios (ch. 13) go further.

### Not applicable
Shorting and borrow costs (long-only spot), stop-out/margin calls, fundamental data release dates (unless added), survivorship of equities (adapted to token survivorship under O5).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 trial ledger | very high | – | – | low–medium | run storage |
| 2 | O2 PBO via CSCV | very high | – | – | medium | per-run return series; O1 |
| 3 | O3 deflation (needs ch. 14) | very high | – | – | low | O1, ch. 14 |
| 4 | O5 sanity-check list | high | – | – | low–medium | other items |
| 5 | O4 research vs evaluation flow | high | medium | – | medium | O1 |
| 6 | O6 multi-asset check | medium | – | – | medium | data import |
| 7 | O7 scenarios | high | – | – | high | ch. 12–13 |

## 5. Affected files
`backtesting` (trial table, sweep service hooks, persistence of per-run returns), `analytics/domain` (CSCV/PBO function, performance degradation regression), `docs/openapi.json`, app sweep result page (PBO card, logit histogram, degradation scatter), app research/evaluation labels, tests.

## 6. Incremental plan
1. Trial ledger and visible counts.
2. Persist per-period returns for sweep members (or recompute on demand from stored seeds).
3. PBO calculator and sweep card.
4. Link to deflated Sharpe (ch. 14) and promotion gates (ch. 1 O1).

## 7. Acceptance criteria and tests
* CSCV: for a hand-constructed 8×4 matrix the enumerated combinations, ranks and logits equal the hand-calculated ones; noise-only matrices produce PBO ≈ 0.5 on average over seeds; a matrix with one clearly superior column gives PBO ≈ 0; deterministic; column order irrelevant.
* Ledger counts equal executed runs; existing endpoints unchanged apart from added fields; ruff, mypy, existing tests green.

## Caveats
The PBO example (0.74) and degradation regression are the book's illustration, not an exhaustive validation (the original paper provides experiments). PBO measures the tendency of selecting the in-sample best to underperform out-of-sample **within the set of trials provided**; it cannot account for trials not recorded. It uses the order-preserving blocks but assumes some stability between blocks; with strong regime changes, low PBO may reflect only that the same regime dominates. The statement "a backtest does not prove anything" is the author's stance; the book still relies on backtests for the later metrics.
