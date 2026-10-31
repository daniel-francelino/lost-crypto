# Book 3 · Chapter 2 — The Illusory Validity of Subjective Technical Analysis

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** this 70-page chapter (pp. 33–102) is a review of cognitive psychology. I read its section structure (35–101) and in full the passages on overconfidence (45–46), confirmation bias (62–63), illusory correlation (72–73), the representativeness heuristic and random-looking charts (93–94) and the clustering illusion (100–101). The remaining passages (anchoring-type effects, hindsight, second-hand information, detailed experiments) were skimmed by heading only and are not summarised in detail.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Subjective technical analysis is not legitimate knowledge; the mind is a natural pattern finder; weird beliefs are common. | Why intuitive chart reading feels valid. | 35–41 |
| C2 | **Overconfidence bias**: self-assessments exceed reality, most extreme for difficult/impossible tasks; **confidence rises with the amount of information, not accuracy**; agreement among redundant inputs (many indicators measuring the same thing) raises confidence without justification. Examples: physicians 88% confident, 20% correct; managers 90% confident, 50% correct. | Combining many indicators subjectively. | 45–46 |
| C3 | **Second-hand information bias**: a good story is persuasive. | Narratives instead of evidence. | 58–61 |
| C4 | **Confirmation bias**: existing beliefs filter evidence; with chance successes a useless method gains credibility over time, and the **most experienced users of a useless method are the least able to see its flaw**; motivational factors (financial and emotional investment, cognitive dissonance) and biased searches reinforce it. | Learning from experience goes wrong. | 62–71 |
| C5 | **Illusory correlation**: any signal-and-outcome claim is a 2×2 contingency table (signal present/absent × outcome occurs/not). People weigh the "upper-left cell" (signal and outcome) and neglect false positives, false negatives and true negatives. | Judging a signal from memorable hits. | 72–81 |
| C6 | **Representativeness heuristic and false stereotype of randomness**: random data (e.g. a 300-coin-flip chart) shows apparent patterns; people mistake that for structure (clustering illusion); a gambler's-fallacy believer is also rewarded by chance. Random walks can trace the shapes chartists prize. | Seeing patterns in noise. | 93–101 |
| C7 | The antidote is the scientific method (Chapter 3). | – | 101 |

## 2. Diagnosis (verified in code and UI)

The chapter concerns the human operator. The system already avoids subjective methods (all strategies are code). What matters is whether the **product helps the operator avoid these biases**.

| Concept | Status | Evidence |
|---|---|---|
| Objective rules only | ✅ | See book 3 ch. 1. |
| Confidence from agreement of redundant inputs | ⚠️ | Strategies use one indicator family each; if combinations are added the framework has no check for redundancy between conditions. |
| Confirmation bias in research | ⚠️ | Sweeps display results; nothing records how many alternatives were tried, and the operator can pick the best run (book 1 ch. 3 O7, book 2 ch. 1 O5). |
| Illusory correlation (only seeing hits) | ❌ | Backtest detail lists round trips; there is no table of **signals followed by a move vs signals not followed**, nor the base rate of the outcome without a signal. |
| Seeing patterns in noise | ❌ | Equity curve and candle charts are shown alone; nothing shows what a no-skill rule's equity looks like on the same data. |
| Narrative bias | ✅/n.a. | The app shows numbers and audit trails, no commentary. |

## 3. Opportunities

### O1 — Signal contingency table and base rate *(book: C5, pp. 72–81)*
* **Problem:** a strategy's entries are judged by the trades we remember, not by all four cells.
* **Proposal:** in the diagnostics, for a chosen forward horizon `h` and outcome definition (for example "forward return after costs > 0"), report the 2×2 table: entries followed by a positive outcome, entries followed by a non-positive outcome, non-entry bars followed by a positive outcome, non-entry bars followed by non-positive; with the **base rate** of a positive outcome on all bars and a hit-rate comparison. For long/flat strategies "non-entry" means bars where the strategy is flat.
* **Benefit:** directly answers the book's question (is the signal better than the unconditional frequency?). **Complexity:** low. **Risks:** a significant difference in a 2×2 table still needs a test and a multiple-testing correction (next chapters); overlapping horizons are not independent (see book 2 ch. 6 O1). **Validation:** synthetic data with a planted signal vs noise; counts match hand tabulation.

### O2 — "Could this be luck?" visual: the strategy's equity beside placebo equities *(book: C6, pp. 93–101 · adaptation)*
* **Proposal:** on the backtest page, draw the strategy's equity curve together with a fan of equity curves from random-entry runs (same trade count and holding period; see book 2 ch. 1 O1 stage 2, book 3 ch. 1 O2). Seeing that no-skill rules can also look impressive calibrates intuition. **Complexity:** medium (the placebo engine is shared). **Risk:** visual clutter, performance; compute the fan on demand. **Validation:** UI test with fixed seed.

### O3 — Pre-registration of hypotheses and parameter ranges *(book: C4, pp. 62–71 · adaptation)*
* **Proposal:** before a sweep or a significant experiment, the operator can record the hypothesis, the parameter ranges to be tried and the success criterion (extends the notes proposed in book 2 ch. 4 O1); the result page then shows whether the final choice was inside the pre-registered plan. **Complexity:** low–medium. **Risk:** friction; use as an optional discipline. **Validation:** API test linking a plan to a sweep.

### O4 — Warn about redundant conditions *(book: C2, p. 46)*
If a combined strategy is built, compute the correlation between its condition signals and warn when they are largely redundant (they add confidence, not information). Defer until a multi-condition strategy exists. **Complexity:** low–medium.

### Not applicable
Teaching materials on perception experiments; subjective chart patterns.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 contingency table + base rate | high | – | – | low | diagnostics module (book 2 ch. 2 O1) |
| 2 | O3 pre-registration | medium | – | – | low–medium | notes (book 2 ch. 4 O1) |
| 3 | O2 placebo fan chart | medium | – | – | medium | placebo engine (book 2 ch. 1 O1) |
| 4 | O4 redundancy warning | low | – | – | low–medium | multi-condition strategy |

## 5. Affected files
`analytics/domain/` (contingency counts), market-data diagnostics endpoint, `backtesting/application/service.py` (plans), app backtest detail and market-data pages, tests.

## 6. Incremental plan
1. Contingency table inside the diagnostics module.
2. Hypothesis/plan records (notes).
3. Placebo fan chart once the random-entry runner exists.

## 7. Acceptance criteria and tests
* The table's four cells sum to the number of observations; base rate equals the unconditional frequency.
* Placebo runs are deterministic for a seed.
* No change to trading behaviour; ruff, mypy, existing tests green.

## Caveats
The experiments cited (physicians, managers, earnings forecasts) are the author's literature review and are not re-verified here. Knowing about the biases does not remove them; the proposals only add friction and counterfactual views.
