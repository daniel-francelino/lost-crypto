# Book 3 · Introduction and Chapter 1 — Objective Rules and Their Evaluation

*Evidence-Based Technical Analysis*, David R. Aronson (Wiley, 2007). Book pages (PDF page = book page + 16). The PDF is an OCR scan; formulas were checked against the surrounding text. Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. Introduction (pp. 1–11) and Chapter 1 (pp. 15–31) were read in full.

## 1. Summary (pp. 1–31)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | A claim must have **cognitive content** (a discernible-difference test): it must be possible to tell whether it was right or wrong. Knowledge = justified true belief; scientific knowledge stays provisional. | Vague, untestable forecasts. | 2–5 |
| C2 | **Objective vs subjective** technical analysis. Programmability criterion: a method is objective iff it can be coded to output unambiguous positions. Subjective methods (chart patterns, Elliott wave) are rejected as untestable. A profitable back test of an objective method is *necessary but not sufficient*: it can be luck or **data-mining bias**; "advanced statistical inference" (Chapters 4–6) decides. | What counts as evidence. | 5–7, 15–16 |
| C3 | Cited academic findings (author's selection, no new evidence here): trend indicators work in commodities and FX; simple rules on young-company indices; chartists cannot tell real from random charts; head-and-shoulders adds nothing on stocks. | Context. | 8–9 |
| C4 | **A rule** maps input series to a position series (+1/−1 or 0); **binary reversal rules** (always long or short) are used; thresholds can be fixed (for stationary inputs) or variable (moving average; bands/Bollinger), possibly with **flip-flop** logic (two events). Single-threshold rules give mutually exclusive, exhaustive states. | Formal rule definition. | 16–21 |
| C5 | **Traditional and inverse rules**: test the opposite interpretation as well, since the traditional reading may be wrong or the input may have no obvious reading. | Not assuming the sign of an effect. | 21–22 |
| C6 | **Benchmark = a rule with no predictive power** (like a placebo), not zero and not necessarily buy-and-hold; to count, a rule must beat it by a margin that excludes chance (Chapters 4–6). | What to compare against. | 22–23 |
| C7 | **Position bias × market trend**: a rule's back-tested return = predictive component + an unwanted component from (1) the share of time long vs short and (2) the market's average daily change in the sample. Expected return of a random rule: `ER = p(L)·ADC − p(S)·ADC`. Example: S&P 500 1976–2004, ADC +0.035%/day (9.22%/yr): a random rule long 90% of the time earns about 7.31%/yr, one long 60% about 1.78%/yr, with **no** predictive power. A rule can have a bias that comes from asymmetric long/short conditions (a restrictive short condition). | Rules that merely hold the market's drift. | 23–27 |
| C8 | **Remedies**: subtract the expected return of a non-predictive rule with the same position bias, or, equivalently (proof in the appendix), **detrend** the market's daily returns by subtracting their sample average; detrended data is used only to compute rule returns, signals still use real prices. Use **log returns** (`ln(P_t/P_{t-1})`). | Fair evaluation. | 27–29 |
| C9 | **Look-ahead and execution price**: if a signal uses the close, the earliest fill is the **next open**; daily rule return = position at close of day 0 × `ln(Open_{t+2}/Open_{t+1})` minus the average log return; lagged or revised inputs must be lagged. | Leakage. | 29–30 |
| C10 | **Trading costs**: needed if the rule is used stand-alone; the author omits them in his case study because the aim is to find predictive information. | Costs vs signal discovery. | 31 |

Not covered here: Chapters 2 (psychology of subjective belief, pp. 33–102) and 3 (scientific method, pp. 103–164) are separate reports.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| C2 programmability, objective rules | ✅ | All strategies are code (`strategies/domain/*`) producing signals; nothing subjective. |
| C4 rule formalisation, threshold logic | ✅ | EMA crossover = variable threshold (moving-average cross); Donchian = flip-flop with entry and exit channels. |
| C5 inverse rules | ❌ | Long-only; no systematic test of the opposite interpretation. A short side is impossible in spot. Not applicable. |
| C6 benchmark = random/no-skill rule | ❌ | The only benchmark is buy-and-hold (`buy_and_hold_return_pct`). No "same-exposure random rule" benchmark. |
| C7 position bias × market trend | ❌ **material** | A long-only strategy that is in the market 60% of the time during a strong bull run earns a large positive return with zero skill. Metrics report neither time in market nor an exposure-adjusted benchmark. |
| C8 detrending | ❌ | Not done. |
| C9 look-ahead | ✅ | Fill at the next candle's open (`engine.py`); uses the same convention the book recommends. Daily returns differ: the book uses `ln` returns, the engine tracks equity. |
| C10 costs | ✅ | Always included (the book omits them for discovery, but includes them for stand-alone use, matching ours). |

## 3. Opportunities

### O1 — Time-in-market and exposure-adjusted benchmark *(book: C6–C8, pp. 22–29 · long/flat adaptation is our derivation)*
* **Problem:** a long-only bot reports "+40% vs buy-and-hold +60%": we cannot tell skill from the market's drift. The book shows that the right yardstick is *what a no-skill rule with the same exposure would have earned*.
* **Proposal:** add to the metrics: (a) `time_in_market` (share of bars with a position); (b) `exposure_adjusted_benchmark_pct`: for a long/flat rule the expected return of a no-skill rule with exposure `p(L)` is `p(L) × market return` (our derivation from the book's formula `ER = p(L)·ADC − p(S)·ADC`, which assumes long/short reversal rules, with `p(S) = 0` for long/flat); (c) `excess_vs_exposure_pct = strategy return − benchmark`. For multi-period, work in log returns with the sample average as in C8. The book's detrending result is for long/short rules; the long/flat adjustment is a derivation to be verified by simulation (Monte Carlo with random positions at the same exposure).
* **Benefit:** the most direct, cheap fix for bull-market illusion in crypto; complements buy-and-hold. **Complexity:** low (pure functions on the equity curve and fills).
* **Risks:** the adjustment is first-order (it treats exposure as independent of returns, as the random rule does); with high volatility the sampling noise of the benchmark is large (Chapters 4–5); costs are not part of the benchmark and must be added consistently.
* **Validation:** simulate random long/flat positions with a given exposure on a trending series: average excess must be ≈ 0; reproduce the book's 7.31% and 1.78% numerically from the stated inputs (ADC 0.035%/day, 90% and 60% long).

### O2 — Placebo comparison (random-entry benchmark) *(book: C6, p. 23)*
Re-using the random-entry test proposed in [book 2 ch. 1 O1 stage 2](../02-algorithmic-trading-chan/ch01-backtesting-and-automated-execution.md): replace the strategy's entries by random ones with the same trade count and holding period and show where the strategy falls in that distribution. This is the book's "placebo" idea made practical. Cross-reference only; implement once.

### O3 — Report the longest-only / long-bias explicitly *(book: C7, pp. 24–26)*
Show "% of bars long" and "market return over the run" next to every result and in sweeps so that rankings are not dominated by rules that simply stay long more often. Part of O1; no extra work beyond the display. **Complexity:** very low.

### O4 — Keep the execution convention; document the log-return convention *(book: C8, C9, pp. 28–30)*
The engine already fills at the next open. Document in `docs/` that metrics use equity changes, and decide whether new statistics (O1, book 1 ch. 2 O1) use simple or log returns. Recommend log returns for statistical tests, simple for reporting. **Complexity:** very low.

### Not applicable
Inverse rules (no shorts), subjective TA, long/short bias with a short leg, omitting costs.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 time-in-market + exposure benchmark | **high** | – | – | low | – |
| 2 | O3 display of bias | medium | – | – | very low | O1 |
| 3 | O4 convention note | low | – | – | very low | – |
| 4 | O2 placebo distribution | high | – | – | medium | book 2 ch. 1 O1 |

## 5. Affected files
`analytics/domain/metrics.py` (new fields), `backtesting/domain/segments.py` (per-segment equivalents), `analytics/presentation/schemas.py`, `docs/openapi.json`, app metric cards and sweep table (`components/backtests`), tests (`api/tests/unit`), docs.

## 6. Incremental plan
1. Pure functions: time in market, exposure-adjusted benchmark, excess; unit tests incl. the book's numbers.
2. Add as additive metric fields (train/test too); show in the app.
3. Add the same fields to sweep results so the ranking can use excess instead of raw return.

## 7. Acceptance criteria and tests
* The book's 7.31% / 1.78% examples are reproduced from ADC and exposure.
* Random long/flat simulations at fixed exposure give mean excess ≈ 0 within sampling error.
* Existing metrics, stored runs and API shapes unchanged except for new optional fields.
* ruff, mypy, existing tests green.

## Caveats
The S&P 500 numbers are examples; the benchmark logic removes only the first-order drift effect and does not by itself prove skill. Back-test profitability is not evidence of future profitability, as the author stresses (p. 6).
