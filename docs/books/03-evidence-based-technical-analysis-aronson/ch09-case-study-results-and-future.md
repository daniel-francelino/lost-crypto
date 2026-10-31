# Book 3 · Chapter 9 — Case Study Results and the Future of TA (and Appendix)

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 441–448, 455–465 and the heading structure of 449–454 and 466–474 were read. The table of the top 100 rules (pp. 445–446) was only glanced at. The remaining critique-of-case-study text (449–454), the end of the discussion of machine-learning combinations (465–474), the **Appendix** (the proof that detrending equals benchmarking on position bias, pp. 475–476) and the notes were **not** read in detail.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Result:** none of the 6,402 rules had a mean return high enough to reject the null at 0.05 after adjusting for data mining. The best rule earned **10.25%/yr on detrended data**; its data-mining-adjusted p-value was **0.8164** (bootstrap) and **0.8194** (permutation), and it fell *below* the centre of the sampling distribution. | The honest outcome of a big search. | 441–442 |
| C2 | **The best-of-N null is centred away from zero:** for these 6,402 rules the expected return of the best of N useless rules is about **11%/yr**, not 0; returns above ~15% would have been significant at 0.05 and above ~17% highly significant (p < 0.001). The number depends on N, observation count, rule correlation and data. | Calibration of "how good must it be". | 442–443 |
| C3 | **Naive testing would have misled:** with an ordinary single-rule test the best rule had p = 0.0005, and about **320 of 6,402 rules (≈5%)** would have looked significant at 0.05, exactly what chance predicts. | The scale of fool's gold. | 443–444 |
| C4 | Confidence intervals that account for data mining are *joint* intervals (80%) for all rules (e.g. best rule: −2.9% to +23.5%); three tests were reported (enhanced bootstrap, original Reality Check, Monte Carlo with enhancement). The 5% level carries a 1-in-20 chance of a false rejection even in this design. | Reporting uncertainty. | 444–448 |
| C5 | **Critique (positives):** used a no-skill benchmark; controlled market trend (detrending); controlled look-ahead (next-day open execution); controlled data-mining bias; avoided data snooping. | Design checklist. | 448–449 |
| C6 | **Extensions of the study:** combine rules **linearly** (voting: majority position; **fractional position**: size proportional to net long/short share of rules in a theme, Hsu & Kuan); learning rules (pick the recently best rule); diffusion indicators (share of rules long); inverse rules must be removed or the sum is zero. **Machine-induced nonlinear rules** (neural nets, trees, SVMs, genetic programming) need the search for parameters *and* complexity, and a robust significance test for that did not exist (author's statement, 2007). | Where to go next. | 455–457 |
| C7 | **Three-segment scheme for complexity search**: training, test, **validation**. Inner loop: optimise parameters at a given complexity on training; outer loop: raise complexity while **test** performance improves, stop when it peaks and degrades (the over/underfitting boundary); then the **validation set**, untouched until then, gives the only unbiased estimate (the test set's result is biased by repeated visits). Can be done walk-forward by sliding the tri-part window. Example: 2-parameter MA cross 30% train/15% test; adding an RSI filter (4 parameters) 50%/20%; continue until the test result declines. | Controlling overfit when adding rules. | 457–461 |
| C8 | **Future of TA:** the author argues TA must become evidence-based or be marginalised; experts' forecasts are barely better than non-experts' (Armstrong, Cowles, Hulbert newsletters: fewer than 10% beat a broad index over ten years); EBTA's limit is that controlled experiments are impossible and **the same history is reused**, which feeds the data-mining bias; regression can partly control confounders (Fosback; Jacobs & Levy found one-month reversal of weak stocks to be a strong, consistent TA effect); **human–computer partnership**: humans propose hypotheses and are poor at discarding them; computers can combine many variables but face the **curse of dimensionality** (data density falls exponentially with indicators). | Direction of the field. | 461–465 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Honest reporting of a large search | ❌ | A sweep lists results without the best-of-N reference (see ch. 6). |
| Calibrated threshold for "good enough" | ❌ | No notion of how large a return must be to be unusual for the grid size. |
| Naive vs corrected significance side by side | ❌ | None. |
| Three-segment (train/test/validation) discipline | ⚠️ | Train/test split exists; no validation segment; the test segment is reused by every selection. |
| Linear combination of rules (voting / fractional position) | ❌ | One strategy per bot; position is all-in or flat (the engine/signal contract has no target size). |
| Learning rules (select best recent rule) | ❌ | None. |
| Curse of dimensionality / controlling the number of indicators | ✅ by construction | Strategies are low dimensional. |
| Reuse of one history | ⚠️ | Same candle history for all experiments; count not tracked. |

## 3. Opportunities

### O1 — Show the "required to be unusual" return for the sweep *(book: C2, C3, pp. 442–444)*
* **Problem:** a user sees a +40% result and cannot tell if it is exceptional *for a grid of this size*.
* **Proposal:** from the best-of-N permutation distribution (book 3 ch. 6 O1) show, next to the best result: the median and 95th percentile of the null "best of N", the return needed for p = 0.05 and p = 0.001, and the number of grid cells that would be expected to look significant by chance (≈ 5% × N under independent rules). **Complexity:** low once ch. 6 O1 exists. **Validation:** with a random sweep about 5% of cells exceed the single-rule threshold.

### O2 — Three-segment protocol (train / test / validation) with a locked validation set *(book: C7, pp. 457–461)*
* **Proposal:** extend the backtest configuration from `test_fraction` to an optional `validation_fraction`; the validation segment is **hidden from sweeps and ranking**, evaluated only when the operator *commits* a chosen configuration, and the commit is recorded (audit) so the segment is known to be consumed. After consumption, the system warns that the segment can no longer give an unbiased estimate (book 3 ch. 6 C7). **Complexity:** medium (segments, locking state, UI). **Risk:** operator can create new "validation" data by changing dates; the audit and the universe count (ch. 6 O2) limit that. **Validation:** API tests: ranking ignores the validation segment; second evaluation of the same segment is flagged.

### O3 — Complexity-stopping rule *(book: C7, pp. 459–461)*
When a user adds conditions or parameters, report train and test performance by complexity level and flag the first level at which test performance stops improving (the over/underfitting boundary). Practical form: record the sequence of strategy variants (by number of parameters) in a study and chart train vs test. **Complexity:** low–medium (studies from book 3 ch. 2 O3 and ch. 6 O2). Only meaningful after more than one family of strategy exists.

### O4 — Linear rule combination as a research idea *(book: C6, pp. 455–456)*
Voting or fractional-position combination of several simple rules in one theme is the book's suggested next step. It requires (a) multiple strategies inside one bot or a combined-signal strategy and (b) a target-position signal (partial sizes) in the signal contract (the same prerequisite as B-SCALE-IN and B-TRANCHES). Record as **H-VOTE**; do not build before significance tooling exists and before those backlog items are decided. Inverse rules are not applicable (long-only).

### O5 — Regression to control confounders in diagnostics *(book: C8, p. 464 · pointer only)*
The book cites regression-based "purified" indicators; a crypto analogue would regress a strategy's per-bar returns on market-wide factors such as BTC returns to isolate non-market performance. This is our adaptation; it needs a multi-asset context (B-MULTI-ASSET) and should wait.

### Not applicable
Rankings of newsletters and experts; the Appendix proof was not read but its result (detrending is equivalent to a same-bias benchmark) is applied in book 3 ch. 1 O1.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 required-return display | high | – | – | low | book 3 ch. 6 O1 |
| 2 | O2 locked validation set | **high** | – | – | medium | book 3 ch. 6 O2 |
| 3 | O3 complexity stop | medium | – | – | low–medium | studies |
| 4 | O4 voting | medium | – | – | high | signal contract |
| 5 | O5 regression | low | – | – | high | multi-asset |

## 5. Affected files
`backtesting/domain/models.py` (`validation_fraction`), `backtesting/domain/segments.py`, `backtesting/application/service.py` (commit/lock flow), audit events, `docs/openapi.json`, app backtest and sweep pages, tests.

## 6. Incremental plan
1. Required-return display after the best-of-N machinery.
2. Validation segment with commit/lock and audit.
3. Study-level train/test-by-complexity chart.
4. Voting/fractional position as a separate design (needs the signal contract decision).

## 7. Acceptance criteria and tests
* Rankings and sweeps never read the validation segment before commit.
* The second evaluation of a consumed validation set raises a visible warning and an audit record.
* Existing runs and APIs remain compatible; ruff, mypy, tests green.

## Caveats
The outcome that **no rule was significant** is a result for S&P 500 data from 1980–2005 and these rules; it is neither proof that technical rules never work nor that crypto rules do not. The author expects effects to be weak and rare, which is why the interesting question is how to evaluate a search, not which rule won.
