# Book 5 · Chapter 12 — Backtesting through Cross-Validation

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 161–168 were read (walk-forward and its pitfalls, CV backtesting, combinatorial purged CV, how CPCV addresses overfitting, exercises). The expected-maximum formula text on p. 166 was partly garbled by extraction and is cited only qualitatively.

**Relevance:** it supplies the book's answer to "a single historical path is easy to overfit": generate **many out-of-sample paths** from the same history. For a rule-based platform this matters mostly for strategies with *learned or optimised parameters* (every sweep-and-pick procedure is a learner), so CPCV applies to the "optimise on training blocks, test on held-out blocks" procedure.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Two ways to use past data: (1) simulate how the strategy would have performed historically (**walk-forward, WF**), (2) simulate **scenarios that did not happen**. "Backtest" has become a synonym of WF. No generic recipe; each backtest must be customised to the strategy. | Two backtest paradigms. | 161 |
| C2 | **WF advantages**: clear historical interpretation (reconcilable with paper trading); history is a filtration so trailing data guarantees OOS (given purging; a common error is leakage when `t1.index` is in training and `t1.values` in testing). No embargo needed. **WF pitfalls**: (1) a **single path** is tested and can easily be overfit; (2) results depend on the **sequence** of data (training on a bear market then a rally vs the reverse); "it is as easy to overfit a walk-forward backtest as a walk-backward one" and inconsistent outcomes under reversal are evidence of overfitting; (3) early decisions use few data — with a warm-up `t₀` of `T`, half of decisions use on average only about `(3/4)·t₀/T + 1/4`... of the observations (the book's expression: about `3t₀/(4T) + 1/4` of the sample). | Limits of walk-forward. | 161–162 |
| C3 | **CV backtests** (train on all periods except the test period, e.g. test 2008 with a model trained on 2009–2016): not historically accurate but a **stress scenario** for a strategy "ignorant of" that period. Advantages: not tied to the historical sequence; every decision is made on equal-sized training sets; every observation tested once (longest OOS). Disadvantages: still one path; no historical interpretation; leakage possible because training does not trail testing (needs purging/embargo, ch. 7). | Scenario-style testing. | 162–163 |
| C4 | **Combinatorial purged cross-validation (CPCV)**: partition `T` observations into `N` ordered groups; every combination of `k` groups forms a testing set (`C(N, k)` splits); each group appears in `φ[N, k] = k·C(N, k)/N` testing sets, which are recombined into **`φ` distinct backtest paths** (example `N = 6, k = 2`: 15 splits, 5 paths, training share `1 − k/N`); purge and embargo as in ch. 7; yields a **distribution of Sharpe ratios** (one per path) instead of one number. `k = 1` reduces to CV; `k = 2` gives `N − 1` paths with a training share `1 − 2/N`; choose `N = φ + 1`; limit `k ≤ N/2`. | Many paths from one history. | 163–166 |
| C5 | **How CPCV addresses backtest overfitting**: the expected maximum of `I` IID standard normal Sharpe estimates grows with `I` (≈ `(1−γ)Z⁻¹[1−1/I] + γZ⁻¹[1−1/(Ie)]`, γ = Euler–Mascheroni 0.5772), i.e. selection bias grows with the number of trials; WF and CV estimate the Sharpe from one path (high variance); CPCV averages `φ` paths: `σ²[mean] = φ⁻¹σ²(1 + (φ−1)ρ̄)`, lower than a single path when the average correlation `ρ̄ < 1`, so false discoveries drop (bias is not "eliminated"; the variance shrinks). A reviewer can ask for a CPCV with `N, k` chosen after the fact, defeating overfitting to a particular path. | Variance of the performance estimate. | 166–167 |
| C6 | Exercises: reversal tests, warm-up selection bias, WF vs CV selective reporting, how many (`N, k`) give 1,000 paths for 100,000 forecasts, ethics of withdrawing a paper after a failed CPCV (negative Sharpe mean −1, sd 0.5). | Practice. | 167–168 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Historical single-path backtest | ✅ | The backtest runs once over the chosen period. |
| Reverse-sequence sanity test | ❌ | Not available (nor meaningful for all strategies; it is a diagnostic of overfit in parameter-learning procedures). |
| WF/rolling re-optimisation | ❌ | B-WALK-FORWARD proposed (book 4 ch. 21 O4). |
| CV or CPCV | ❌ | None. |
| Distribution of performance over many paths | ❌ | One number per backtest and one list per sweep. |
| Warm-up handling | ✅/⚠️ | Indicators need history (strategy warm-up); results computed over the whole period after warm-up; the effective sample size per decision is not an issue for non-learning rules. |

## 3. Opportunities

### O1 — CPCV for any procedure that **chooses parameters from data** (the sweep-and-select pipeline) *(book: C4, C5, pp. 163–167)*
* **Proposal:** treat "sweep on training blocks → pick best → test on held-out blocks" as the learner; implement CPCV over the platform's chronological candles: `N` ordered groups (e.g. 8–12 blocks), `k = 2` held out; for each of `C(N, 2)` splits, run the sweep on the purged/embargoed training blocks (reuse the sweep engine with `MAX_SWEEP_RUNS` per split), apply the selected parameters on the held-out blocks, and **recombine** the held-out segments into `N − 1` full-length out-of-sample paths. Report the distribution (mean, median, std, share of negative paths) of Sharpe/return/drawdown across paths and the stability of selected parameters across splits.
* **Why:** a single OOS number is noisy and path-dependent; the distribution answers "how might this selection procedure have performed" including its failure rate. It also integrates with PBO (ch. 11 O2) and the deflated Sharpe (ch. 14).
* **Cost/risks:** compute grows as `C(N, 2) ×` sweep cost (N = 10 → 45 sweeps); open positions and indicator state at group boundaries require purge/embargo (ch. 7 O1); each path stitches segments from different models (the stitched equity curve can have jumps, and positions must be closed at boundaries or valued consistently); crypto history is short (N groups of a few months, so each group is a distinct regime and results are noisy); the paths are correlated because they reuse the same groups (the book's `ρ̄`). **Complexity:** high. **Validation:** with a no-edge random-walk dataset, the path distribution is centred near zero (minus costs) and the share of positive paths is not systematically high; with a planted edge it is positive across paths; no training observation inside any held-out interval ± embargo; count of paths equals `φ[N, k]`.

### O2 — Reverse-sequence consistency check as a cheap overfitting diagnostic for sweeps *(book: C2, p. 162)*
Run the same sweep-and-pick procedure on the **time-reversed** series (for symmetric strategies like trend following on long/short; for long-only the reversal turns uptrends into downtrends so results differ for an economically legitimate reason—state this caveat) and compare. The book's argument: if WF were truly informative about the future, forward sequences should systematically beat reversed ones; inconsistent outcomes indicate overfit procedures. Provide as a **research diagnostic only**, with the long-only caveat. **Complexity:** low–medium. **Risks:** misinterpretation for long-only spot; not applicable as pass/fail.

### O3 — Held-out-period stress scenarios using CV logic (train excluding the stress period) *(book: C3, pp. 162–163)*
Provide named test periods for crypto (e.g. 2018 bear market, March 2020 crash, 2021 top, May 2022 Luna/FTX-style stress, 2022 bear): evaluate a configuration chosen on data **excluding** the stress period on that period, to show how a strategy "ignorant" of the crisis would have behaved. Makes the shock analysis (book 4 ch. 21 O5) and period-representativeness checks concrete. **Complexity:** low–medium (period list + segmentation + purge). **Validation:** the selected parameters do not depend on the held-out period (property test); results reproducible.

### O4 — Report the sample used per decision for rolling/WF procedures *(book: C2, p. 162)*
When B-WALK-FORWARD is built, report the average and minimum amount of data available at each decision (warm-up effect: early decisions use few observations). The book's expression shows only a fraction of the total sample informs half the decisions. **Complexity:** low.

### Not applicable
Exercise discussion on journals' ethics; the exact asymptotic expected-maximum formula (re-derived in chapter 14).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 held-out stress periods | high | medium | – | low–medium | segmentation + purge (ch. 7 O1) |
| 2 | O4 sample-per-decision report | low | – | – | low | walk-forward |
| 3 | O2 reverse-sequence diagnostic | low | – | – | low–medium | – |
| 4 | O1 CPCV for the sweep-and-pick | high | – | – | high | ch. 7 O1, ch. 11 O1–O2 |

## 5. Affected files
`backtesting/application` (CPCV orchestration over sweeps; job execution — long running, should be a background job like existing worker processes), `backtesting/domain/segments.py` (group splitting, purge/embargo, path recombination), `analytics/domain` (path statistics), `docs/openapi.json`, app (paths distribution view), tests.

## 6. Incremental plan
1. Stress-period held-out evaluation (O3) on top of purge/embargo.
2. Walk-forward (book 4 ch. 21 O4) then CPCV orchestration as a background job.
3. Combine with PBO and deflated Sharpe for a "selection credibility" panel.

## 7. Acceptance criteria and tests
* `φ[N, k]` and the split count match formulas (`N = 6, k = 2 → 15, 5`); every group is tested in exactly `φ` splits; each path covers every group exactly once; purged training sets never intersect held-out intervals plus embargo; deterministic given a seed; ruff, mypy, existing tests green.

## Caveats
The book presents CPCV as its own invention and gives no empirical study in these pages of its false-discovery rate (that is deferred to cited papers and later chapters); the variance reduction argument depends on the average path correlation, which is high when paths share groups. The exercise answers are not given. The WF vs reversed-series argument is an argument by example, not a theorem. For a long-only rule-based strategy with 2–3 parameters, simpler tools (plateau analysis, PBO) provide most of the benefit at far lower cost.
