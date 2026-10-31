# Book 3 · Chapter 3 — The Scientific Method and Technical Analysis

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** the chapter (pp. 103–163) is largely a history and philosophy of science (Greek science, induction, deduction, Popper, Kuhn, and others; pp. 104–143). I read its structure and, in full, pp. 107–109 (objectivity and the nature of scientific knowledge) and pp. 144–147 and 160–163 (the hypothetico-deductive method, the worked technical-analysis example, the objectification of the head-and-shoulders pattern and the four subsets of technical analysis). The philosophical history in pp. 104–143 was **not** read beyond headings and is not summarised.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Scientific knowledge is **objective** (shareable and verifiable), **empirical** and **quantitative**; subjective experience cannot be verified by others. Prefer simpler explanations (a random walk over Elliott waves, unless the complex theory predicts better). | What qualifies as evidence. | 107–109 |
| C2 | **Hypothetico-deductive method**: observation → hypothesis (that the pattern is not an artefact of the sample) → prediction (a conditional: *if the hypothesis is true, X will be observed in new data*) → verification on new observations → conclusion by statistical inference. Stages blur in practice. | A procedure for claims. | 144–145 |
| C3 | **Logic of testing**: a profitable back test cannot prove the hypothesis (affirming the consequent is a fallacy); an unprofitable one can refute it (falsifying the consequent). Hence formulate a **null hypothesis** (the rule does not make money) and *refute the null*; the chain of reasoning is valid only with new, relevant observations and proper statistics. | Why "it worked in the backtest" isn't proof. | 145–146 |
| C4 | **Rigorous analysis of results**: extraordinary performance should first be explained by mundane causes: **sampling luck** and **data-mining bias**, before accepting that a rule has predictive power. | Skepticism toward good results. | 146–147 |
| C5 | Key points: a hypothesis can never be conclusively proven; testable only if predictions about *yet-to-be-made* observations can be deduced; a hypothesis that only explains the past is not scientific; compare predictions with new observations. | Rules of evidence. | 147–148 |
| C6 | **Objectifying a subjective pattern**, example: the head-and-shoulders pattern. The study cited (Chang & Osler, "C&O", 3,100+ signals, 1962–1993) builds a benchmark from **pseudo-price histories: actual price changes strung together in random order**, which keep the statistics of real stocks but destroy temporal structure; patterns still appear in the fake data; real H&S signals lost about 0.25% over 10 days vs 0.03% in pseudo data. A second study (Lo et al.) could not reject "useless". Another source is dismissed because its pattern is not objectively defined and ignores market trend. | A concrete placebo design. | 160–161 |
| C7 | **Four subsets of TA**: subjective; objective with unknown significance; objective, tested and **not significant** ("useless", the likely majority: *most proposed ideas fail in every science*); objective and significant. EBTA = the last two. What matters is *having a procedure to get rid of methods that do not work*. Most rules will probably add value only when combined. | Classification and culling. | 161–163 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Objective, quantitative, repeatable tests | ✅ | Deterministic backtests with a recorded seed and candle SHA-256 (`backtesting/domain/models.py`). |
| Null-hypothesis framing | ❌ | No statement of H₀, no p-value (book 2 ch. 1 O1). |
| Testing on *new* observations | ⚠️ | A chronological hold-out exists; paper trading is mandatory before live (`live_min_paper_days`), which is a prospective test. Neither is linked to a stated hypothesis. |
| Pseudo-price (shuffled-change) benchmark | ❌ | Not implemented. |
| Classification and culling of useless rules | ❌ | No strategy-lifecycle states (hypothesis → tested → useless/useful) and no record of failures. |
| Combination of weak rules | ❌ | Strategies are standalone. |

## 3. Opportunities

### O1 — Shuffled-return placebo (pseudo-price histories) *(book: C6, pp. 160–161)*
* **Problem:** to know if a strategy has any skill on a series, compare it with the same strategy run on series that keep the return distribution but have no temporal structure.
* **Proposal:** create seeded pseudo-price histories by **permuting the actual per-candle returns** (or sampling them with replacement, a bootstrap variant that is our extension) and run the strategy on N such series; report the distribution of returns/Sharpe and the strategy's rank. This is the concrete "Monte Carlo on simulated prices" test that Chan describes (book 2 ch. 1 O1 stage 3) but with permutation instead of a Pearson-system generator, which makes it implementable without extra statistics. The same machinery supplies the "placebo fan chart" (book 3 ch. 2 O2).
* **Benefit:** a distribution-free null for trend/reversion strategies: the strategy must beat what it earns on trendless data with identical returns. **Complexity:** medium (needs the engine to run on synthetic candle series: reconstruct OHLC from returns; decide how to treat high/low; compute cost; batch jobs).
* **Risks:** permutation destroys volatility clustering, which can make the null *too easy* for breakout strategies (volatility clustering creates apparent trends); block permutation is a mitigation. Compute time for thousands of runs. A single good rank on one series is not proof. **Validation:** a strategy engineered to exploit autocorrelation must rank near the top on real data and mid-pack on shuffled; a random strategy must rank uniformly.

### O2 — Strategy lifecycle and a "graveyard" *(book: C7, pp. 161–163)*
* **Problem:** the system records successes by default; the book stresses that most ideas fail and that the discipline is to retire them with a record.
* **Proposal:** a status on strategy configurations/ideas: `hypothesis → tested_insignificant → useful → retired`, with the evidence (backtest ids, significance, reason for retirement). Surface retired ideas in the app so the same idea isn't re-tried blindly. Ties to the notes/post-mortem items (book 2 ch. 4 O1) and pre-registration (book 3 ch. 2 O3). **Complexity:** low–medium. **Validation:** API tests for transitions.

### O3 — Prediction written before the test *(book: C2, C3, pp. 144–146)*
Make the hypothesis → prediction explicit in the backtest request (what outcome would refute it: for example "the strategy's excess return over its exposure-adjusted benchmark is positive with p<0.05"), stored with the run and compared automatically with the result. This enforces falsifiability. **Complexity:** low–medium; pairs with book 3 ch. 1 O1 (benchmark) and book 2 ch. 1 O1 (significance).

### O4 — Combine weak rules deliberately *(book: C7, p. 163 · hypothesis only)*
The author expects most useful rules to work only in combination. No work proposed before significance machinery exists; record as **H-RULE-COMBINATION**.

### Not applicable
Philosophy-of-science history; the Elliott wave and head-and-shoulders critique (no such strategies).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 prediction stored with run | medium | – | – | low–medium | book 3 ch. 1 O1, book 2 ch. 1 O1 |
| 2 | O2 lifecycle/graveyard | medium | medium | – | low–medium | notes |
| 3 | O1 shuffled-return placebo | **high** | – | – | medium | engine reuse, job runner |
| 4 | O4 combination | – | – | – | – | later |

## 5. Affected files
`backtesting/domain/` (synthetic candle generator, placebo runner), `backtesting/application/service.py` (placebo jobs), `strategies/` metadata, new tables for lifecycle/hypotheses, `docs/openapi.json`, app backtest and strategy pages, tests.

## 6. Incremental plan
1. Store a hypothesis/prediction text with each run (no logic).
2. Lifecycle status and graveyard list.
3. Shuffled-return placebo runner, first with a plain permutation, later block-permutation.
4. Automatic prediction check using significance outputs.

## 7. Acceptance criteria and tests
* Permutation preserves the multiset of returns exactly and is deterministic for a seed.
* Placebo ranks behave as described in the validation notes.
* No change to trading behaviour; ruff, mypy, existing tests green.

## Caveats
The head-and-shoulders findings (−0.25% vs −0.03% over 10 days) concern 1962–1993 US stocks and are not transferable. The chapter argues for method, not for any particular rule. Philosophy sections were not read (see top).
