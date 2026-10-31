# Book 4 · Chapter 9 — Momentum and Oscillators

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 369–379 (momentum), 385–389 (oscillators, RSI and variants) and 426 (final comments) were read. The sections on the divergence index (384–385), stochastic and other oscillators (389–404), double-smoothed momentum, velocity and acceleration, hybrid techniques and momentum divergence (404–425) were **not** read and are not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Momentum = price change over a stated interval** (`M(n) = p_t − p_{t−n}`); speed is momentum divided by `n`; acceleration (rate of change of momentum) is more sensitive still. Momentum is **not volatility** (a round trip gives zero momentum and high volatility). Terminology varies: "ROC" is often used for momentum. | Definitions. | 369–371 |
| C2 | **Momentum vs moving average**: momentum has no lag in the same sense and peaks earlier than a moving average of the same length, at the cost of noise; momentum crossing zero is essentially the same as the moving average turning, so it can serve as a trend signal, with a small band around zero; percentage momentum is better across markets but wrong on back-adjusted futures; "momentum" is also used as price minus its moving average ("relative strength"), which has the same shape and extremes. | Where momentum sits among trend tools. | 372–375 |
| C3 | **Choosing the span**: sample values, or mark the tops and bottoms on a chart and use about half to double the average peak-to-peak span; momentum and oscillators are mostly used for **timing** relative to a longer trend. **Entry timing**: a short momentum (e.g. 6 days) inside a 30–50 day trend offers an entry within about three days. | Using momentum with a trend. | 376 |
| C4 | **Fading extremes** (overbought/oversold): fast momentum fluctuates about zero; slow momentum behaves like a trend. Thresholds may be set visually, as a fraction of the maximum possible momentum, or as a **multiple of the standard deviation of momentum (2σ ≈ 5% of values beyond)**. Entry variants: aggressive (on penetration), minor confirmation (first turn after penetration), major confirmation (penetration back), timing (after n days beyond). Exit variants from "enter the opposite" to **"basic exit at zero momentum" (the benchmark mean-reversion assumption)** to "allow an extended move". The scale of momentum **changes with volatility** over time (the ±30 band of 2006 vs later years), so fixed thresholds drift. | Rule menu and scaling problem. | 377–379 |
| C5 | **Oscillators** are momentum normalised to a bounded range (e.g. divided by its maximum over a rolling window, so a $2 move in 2006 and $8.77 in 2011 for Amazon both score 0.52); the aim is high values at peaks and low at valleys followed by reversals. | Volatility-adjusted extremes. | 385–386 |
| C6 | **RSI (Wilder)**: `RSI = 100 − 100/(1+RS)`, `RS = AU/AD` over 14 days by an average-off update; thresholds 30/70; more stable than momentum since it uses all changes; a 14-day RSI stays extreme for sustained moves; the data show **RSI tops/bottoms cluster near 72 and 32**, so 70/30 "are too close together to be selective"; **1.5 standard deviations** is suggested as a trade-off between trade frequency and risk; smoother variants use n-day changes instead of 1-day; **countertrend using RSI change** (`RSI_t − RSI_{t−k} > a`), **net momentum oscillator (CMO)** `100·(Su − Sd)/(Su + Sd)`, and the **2-day RSI** (replace each 1-day change with a 2-day change; more smoothing and higher volatility). | Oscillator specifics. | 386–389 |
| C7 | **Final comments**: with small intervals these indicators are unstable; **all momentum indicators used against the direction of price are high risk**; they are best as a **timing tool within a trend-following strategy**, with the period tuned so that extremes occur at a chosen frequency: e.g. for a trend trade held about 20 days, if you will wait up to two days to enter, build an oscillator (3 periods on daily bars, 10 on hourly bars) that gives at least one, preferably two, oversold signals in every two-day window, and "you are likely to be buying dips rather than rallies". | How to use them safely. | 426 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Momentum, RSI, CMO, oscillators | ❌ | No such indicators in `strategies/domain`. |
| Entry timing within a trend (pullback entries) | ❌ | Both strategies enter at the signal candle's next open. |
| Thresholds in volatility units | ❌ | None (no standard-deviation or ATR helper yet). |
| Counter-trend mean reversion | ❌ | Not present. |
| Stop and limit logic relevant to timing entries | ⚠️ | Entries are market orders at the next open (`engine.py`, trader); no limit-entry simulation. |

## 3. Opportunities

### O1 — Pullback-entry timing for trend strategies (experiment) *(book: C3, C7, pp. 376, 426)*
* **Proposal:** after a trend entry signal, wait up to `k` bars for a fast oscillator (for example a 3-period RSI or a short momentum) to reach an oversold zone, then enter; if it does not within `k` bars, enter anyway or skip the signal (two variants). Entry price improves on average only if pullbacks are frequent; the cost is a delayed or missed entry. For a long-only spot system this directly implements "buy dips within a trend".
* **Benefit:** potential reduction in adverse entry price and early drawdown; a natural fit for the project's long-only constraint. **Complexity:** medium (oscillator helper, strategy state, parameters `k`, `oscillator period`, `threshold`).
* **Risks:** missing the fat tail (the book warns that anything that delays or filters trend entries reduces the chance of capturing it, ch. 8); three more parameters; correlation with the base strategy. **H-PULLBACK-ENTRY**: run only through the evidence pipeline with the extra parameters counted. **Validation:** truncation test; compare entry price vs the base entry, trade count, and the fraction of signals skipped.

### O2 — Oscillator helpers with volatility-scaled thresholds *(book: C4, C5, C6, pp. 377–388)*
* **Proposal:** pure functions: n-bar momentum, normalised momentum (divided by the rolling range), Wilder RSI by average-off update (`Decimal`), CMO, and thresholds defined as **multiples of the rolling standard deviation** of the indicator (the book's 1.5σ/2σ suggestions) rather than fixed 30/70 or fixed momentum levels. **Benefit:** indicators that remain comparable as crypto volatility regimes change (the book's 2006-vs-2011 scaling example). **Complexity:** low–medium. **Validation:** unit tests against hand computations (RSI of a monotonic series = 100; of an alternating series = 50) and scale-invariance tests.

### O3 — Choose one mean-reversion family and compare, rather than adding many *(book: C6, C7; links to book 2 ch. 3 O1)*
Candidates now on the table: z-score bands (Chan), RSI/oscillator extremes (Kaufman), channel/CCI. To avoid inflating the rule universe with near-duplicates, build **one** parameterised mean-reversion strategy with a selectable trigger (z-score of price vs average, RSI level in σ units) and compare triggers inside a single pre-registered study (book 3 ch. 2 O3, ch. 6 O2). The book's strong warning (counter-trend entries "exhibit high risk") belongs in the strategy description and in the thesis block (book 3 ch. 7 O1). **Complexity:** medium.

### O4 — Show indicator scale drift *(book: C4, p. 379)*
For any oscillator or momentum-based rule, show in the backtest detail the rolling distribution of the indicator (e.g. the value of its 2σ band over time) so a fixed threshold's effective selectivity can be seen drifting. Part of the diagnostics. **Complexity:** low.

### Not applicable
Chart-pattern use of RSI (head and shoulders on RSI), divergence index and momentum divergence (not read), stochastic and other oscillators (not read), long-short fading.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O2 oscillator helpers + σ thresholds | medium | – | – | low–medium | stats helpers |
| 2 | O4 scale drift display | low | – | – | low | O2 |
| 3 | O1 pullback entry experiment | medium | medium | – | medium | O2, pipeline |
| 4 | O3 single mean-reversion family | medium | medium | – | medium | book 2 ch. 2–3 |

## 5. Affected files
`strategies/domain/` (helpers and, later, strategy parameters), catalogue and forms, `analytics/domain/`, app strategy forms, tests (including the truncation test).

## 6. Incremental plan
1. Helpers with fixtures.
2. Display of indicator scale drift.
3. Pre-registered studies for pullback entries and for the mean-reversion trigger comparison.

## 7. Acceptance criteria and tests
* RSI/CMO/momentum helpers reproduce fixtures; thresholds in σ units are scale-invariant under multiplying prices by a constant.
* New strategy options are default-off; existing strategies unchanged; ruff, mypy and tests green.

## Caveats
The book offers no performance numbers for these oscillator uses in the pages read. The RSI statistics (tops near 72, bottoms near 32) come from a 1985 study of futures. Counter-trend trading is described by the author himself as high risk.
