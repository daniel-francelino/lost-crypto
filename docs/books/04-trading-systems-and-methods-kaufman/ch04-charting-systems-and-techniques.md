# Book 4 · Chapter 4 — Charting Systems and Techniques

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 151–153 and 167–180 were read. The section from Dunnigan's thrust method to the action-and-reaction system (pp. 152–166: Nofri congestion, outside/inside days, pivot points) was only skimmed at its start and **not** summarised. Several pages were cut by pdftotext (formulas partly lost; the text of p. 178 prints "13 the number" where a fraction was probably intended).

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Charting methods that can be **automated** are collected; time is unimportant in many of them, only the level. The first systematic traders (Dunnigan's thrust: a swing of a set percentage within a time window, with different swing sizes per market) hold lessons: "what appears unsophisticated may be the key". | Origins of systematic rules. | 151–152 |
| C2 | **Trading at even numbers**: orders cluster at round prices (a New York Fed study is cited for more trading activity around even numbers); moves through round numbers are "minor breakouts"; a trader can place orders just beyond the round number (a short breakout at $60 placed at $60.25) to be ahead of the crowd. | Order clustering. | 167 |
| C3 | **Channel breakout** by two automatable routes: (a) from swing highs/lows and a regression line through recent swing points; (b) a **least-squares straight line on closes** against sequential integers (not dates, because of weekend gaps), parallel lines at the largest deviations `B_U` and `B_L`, **projected one period ahead** by the slope; a close beyond the projected band reverses the trend; near-boundary countertrend entries and scaling-in are possible; exits on a break of the opposite line; using closes is more conservative than highs/lows. | Objective trend channel. | 167–170 |
| C4 | **Moving channel**: centre `M = (H+L+C)/3` averaged over `n` days, range `R` = average range; bands `M_t + (M_t − M_{t−1}) ± f·R/2` projected one day ahead; a close beyond a band triggers entry; profit objective one channel width beyond the breakout, recomputed daily as volatility changes. | Volatility-scaled channel. | 170–171 |
| C5 | **Commodity Channel Index**: `CCI = (typical price − its n-day average) / (0.015 × average deviation)`; best for mean reversion; **simple overbought/oversold rules give frequent small profits and an occasional very large loss** when prices stay overbought for weeks. | Mean-reversion oscillator and its tail risk. | 171–172 |
| C6 | **Wyckoff** (price, volume, point-and-figure and wave charts) and **DeMark's Sequential** (setup of nine closes below the close four days earlier, intersection test, countdown of 13 closes below the close two days earlier, entry options, exits, true-range stops; a pattern that is too specific can only be validated across unrelated markets). | Complex counting patterns. | 172–176 |
| C7 | **Lo, Mamaysky and Wang** (2000): ten formations defined on a kernel-smoothed series (e.g. head-and-shoulders: E3 above E1 and E5; E1/E5 within 1.5% of their average; rolling 38-day window; double top: extrema more than 22 days apart); several hundred US stocks 1962–1996; formations appear far less in synthetic random series; **returns over the next three days were positive for all but one formation and statistically significant for five**; rising volume generally improved results. | Objective pattern detection. | 176–178 |
| C8 | **Bulkowski's rankings** of pattern success (e.g. best bullish: rectangular-top upward breakout, falling-wedge upward breakout…); the author comments that a symmetric-triangle upward breakout in a downtrend behaves opposite to textbook expectations. | Pattern statistics. | 178–179 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Channel breakout (price extremes) | ✅ | `donchian_breakout` implements the n-bar breakout (entry highest-high of the previous `entry_period`, exit lowest-low of `exit_period`). |
| Regression (straight-line) channel with projected bands | ❌ | Not in the catalogue; no regression helper in `strategies/domain`. |
| Volatility-scaled moving channel (range-based) | ❌ | Donchian uses price extremes, not average range; no ATR/range helper. |
| CCI / mean-reversion oscillators | ❌ | No mean-reversion strategy at all. |
| Round-number awareness | ❌ | See book 4 ch. 3 O3 (H-ROUND). |
| Swing high/low detection | ❌ | None. |
| Pattern detection (head-and-shoulders…) | n/a | Subjective-pattern family excluded. |

## 3. Opportunities

### O1 — Regression-channel trend strategy (objective) *(book: C3, pp. 167–170)*
* **Proposal:** a long-only strategy that fits a least-squares line to the closes since a reference point (or over a fixed window), measures the maximum residual excursions `B_U`, `B_L`, projects the channel one bar ahead and enters on a close above the projected upper band while the slope is positive, exiting on a close below the projected lower band. Closes, not highs and lows, as the book recommends for conservativeness.
* **Benefit:** a trend family distinct from moving-average and extreme-breakout rules, with a built-in scaling of the band by the data's own dispersion. **Complexity:** medium (numerical regression in `Decimal`, windowing, new strategy file, app form).
* **Risks:** residual extremes are outlier-sensitive; the line is re-fit each bar, which interacts with look-ahead (must use only data up to the current closed bar: covered by the truncation test); another parameter set to over-fit; the book gives no performance figures for the channel system. **Validation:** truncation test, sensitivity, best-of-N with other trend rules, cost sweep.

### O2 — Volatility-scaled channel (range-based) *(book: C4, pp. 170–171)*
* A simpler alternative: centre = typical price average, bands = ± `f ×` average range, projected one bar ahead with the centre's slope. This adapts to volatility better than raw extremes and is easier than O1. Also gives a **profit objective one channel width away** that updates with volatility. **Complexity:** low–medium. **Risk:** conceptually close to existing trend rules → high correlation among candidates (effective N, book 3 ch. 6 O4). **Validation:** correlation with Donchian runs; truncation test.

### O3 — Shared indicator helpers: average true range, typical price, linear regression *(book: C3–C5)*
Pure functions in `strategies/domain` (with unit tests) reused by O1/O2, by the stop/position-sizing work (volatility-based stops, book 4 ch. 20 and 23) and by diagnostics. **Complexity:** low. **Risk:** more surface; keep one implementation per indicator.

### O4 — Oscillator tail-risk warning *(book: C5, p. 172)*
When a mean-reversion strategy is added, display the author's warning that oscillator rules "give frequent small profits and an occasional very large loss" and require the risk controls described in book 2 ch. 8 (stop beyond the worst backtest excursion, risk budget). Documentation and UI text only for now.

### O5 — Use Lo–Mamaysky–Wang as an example of **objective, falsifiable pattern testing** *(book: C7, pp. 176–178)*
The study defines patterns objectively and tests them against random series, the approach of book 3. If subjective-style patterns are ever added, require this standard (objective definition, synthetic-random control, out-of-sample horizon). No work now. Note the reported effects are for three-day horizons in US stocks, before costs.

### Not applicable
Dunnigan, Nofri, DeMark's Sequential (single-market counting patterns the author himself says can only be validated across unrelated markets), Wyckoff, Bulkowski rankings.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 indicator helpers | – | – | – | low | – |
| 2 | O2 range channel | medium | – | – | low–medium | O3 |
| 3 | O1 regression channel | medium | – | – | medium | O3 |
| 4 | O4 oscillator warning | – | medium | – | very low | – |
| 5 | O5 standard for patterns | – | – | – | none | – |

## 5. Affected files
`strategies/domain/` (new files and helpers), `strategies/catalog.py`, registry, app strategy parameter forms and labels, tests (truncation, parameter validation), `check:consistency`.

## 6. Incremental plan
1. Helpers with unit tests.
2. One new trend channel at a time, each passing the truncation test and cost sensitivity before being exposed.
3. Evaluate through the sweep → best-of-N → validation pipeline (book 3).

## 7. Acceptance criteria and tests
* New strategies are deterministic, parameter-validated, pass the truncation (no look-ahead) test and do not alter existing strategies.
* ruff, mypy and all existing tests green.

## Caveats
Pattern-study returns are 3-day, pre-cost, US-equity figures from 1962–1996. The book itself says the channel techniques are standard but gives no crypto evidence, and a new strategy adds one more entry to the rule universe that the multiple-testing correction must count.
