# Book 3 · Chapter 8 — Case Study of Rule Data Mining for the S&P 500

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 389–402 and 419–422, 437–439 were read in full. The long catalogue of 40 input series, indicator formulas (on-balance volume, money flow, negative volume, advance/decline ratios…, pp. 403–418) and the threshold-crossing rule types (pp. 422–436) were read by heading only. Those parts concern US equity breadth and intermarket data and are not summarised.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Design of the study**: 6,402 individual rules on the S&P 500, Nov 1980–Jul 2005, to demonstrate significance tests that handle data-mining bias (enhanced White Reality Check and Masters' Monte Carlo permutation, both with the Romano–Wolf power improvement). | A worked example. | 389–390 |
| C2 | **Avoiding data-snooping bias**: rules published by others were deliberately excluded because the amount of data mining behind them is unknown; an example (Zweig's double 9:1 volume rule with three free parameters 9, 2 and 3 months) is significant only if its author did not search for those values; the author concedes that earlier reading may still have influenced his choices. | Counting the true universe. | 390–391 |
| C3 | **Statistical definition**: population = the rule's daily returns over the immediate practical future; parameter = expected annualised return; statistic = mean annualised return on **detrended** data; `H₀`: all rules lack predictive power (two formulations: all expected returns ≤ 0 for the bootstrap; random pairing for the permutation); significance level 0.05. **Practical significance differs from statistical**: with 6,000+ observations a negligible edge can be significant; the economic threshold depends on the trader (5% vs 20% expected return). | Pre-specified inference plan. | 391–394 |
| C4 | **Rule themes**: (1) trends via the n-period **channel breakout operator** (CBO: long above the n-day maximum, short below the minimum, current bar excluded); (2) **extremes and transitions** using channel normalisation (stochastic) of a 4-day linearly weighted moving average, with threshold-crossing events; (3) **divergence** between a companion series and the S&P 500 using a doubly channel-normalised indicator. All rules binary ±1; **inverse rules** included. Complex rules (combinations) were not tested, although the author notes complex rules can add value even when components are individually unprofitable. | Rule families. | 391–392, 419–439 |
| C5 | **Operators**: moving average = low-pass filter with lag of `(n−1)/2` days (SMA) versus `(n−1)/3` for a linearly weighted MA; **channel normalisation** `CN = (S_t − min_n)/(max_n − min_n) × 100` removes the trend (a high-pass view); trade-off between lag and false signals; adaptive look-back spans were not used. | Indicator mechanics. | 396–402, 419 |
| C6 | **Parameter grid design**: 11 look-back spans in an approximately **geometric progression with ratio ≈ 1.5** (3, 5, 8, 12, 18, 27, 41, 61, 91, 137, 205 days); naming convention such as `TT-15-137` (type–input–span) because of the number of rules; 858 trend rules = 39 inputs × 11 spans × (traditional + inverse). | Systematic, non-redundant grid. | 419–420 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Channel breakout trend rule | ✅ | `donchian_breakout` (entry channel of previous `entry_period` highs; exit channel of previous `exit_period` lows; current bar excluded) is the book's CBO in long/flat form with a separate exit channel. |
| Moving-average cross | ✅ | `ema_crossover` (exponential; the book uses simple/linearly weighted). |
| Look-back grid design | ⚠️ | Sweeps accept arbitrary lists of values (`create_sweep` over a `grid` dict); no guidance on spacing, so users may pick dense linear grids (many correlated rules, inflating N without adding information). |
| Detrended returns / practical significance | ❌ | Not applied. No notion of a minimum economically meaningful edge. |
| Counting externally sourced rules | ❌ | Not recorded (book 3 ch. 6 O2). |
| Channel normalisation / oscillator rules | ❌ | Not in the catalogue. |
| Intermarket/companion series | ❌ | A bot sees one symbol's candles. |
| Complex/combined rules | ❌ | No framework (also see ch. 9). |

## 3. Opportunities

### O1 — Log-spaced look-back presets for sweeps *(book: C6, pp. 419–420)*
* **Problem:** a linear grid (for example 5, 6, 7, … 50) creates many near-duplicate rules: it inflates N for the multiplicity correction (book 3 ch. 6) while adding no independent information, and costs compute.
* **Proposal:** in the sweep form (app) and the sweep API helper, offer a "geometric grid" generator (`start`, `end`, `ratio ≈ 1.5`) with the book's sequence as a preset and a note that the book chose a ratio of about 1.5 so adjacent spans differ materially. Keep free-form grids available.
* **Benefit:** fewer, more informative runs and a smaller correction. **Complexity:** very low (UI/helper). **Risk:** a coarse grid can miss a narrow optimum, which is acceptable (a narrow optimum is a fragility signal, book 1 ch. 3 C10). **Validation:** unit test of the generator; sweep with the preset produces ≤ 11 values per dimension.

### O2 — Pre-declare the practical-significance threshold *(book: C3, p. 394)*
Let the operator state, before running, the minimum net annual return (after costs) and maximum drawdown that would make a result worth using, and show **statistical and practical significance side by side** (a significant but tiny edge is flagged "not worth trading"). Extends the tolerance idea of book 1 ch. 2 O3. **Complexity:** low.

### O3 — Record the provenance of every parameter set *(book: C2, pp. 390–391)*
Add a `source` to backtest configurations (own idea, published paper/blog, previous sweep winner, default) and include published or inherited parameter choices in the universe count, because their search history is unknown (the Zweig example). **Complexity:** low. **Validation:** API test of the field and of the universe count including externally sourced entries.

### O4 — Oscillator/channel-normalisation indicator as a reusable building block *(book: C4, C5, pp. 401–402, 421)*
A pure function `channel_normalize(series, n)` (stochastic-style), plus WMA, in `strategies/domain` as shared helpers would make a mean-reversion strategy (book 2 ch. 3 O1) and a regime-neutral oscillator simple to express with a *fixed* threshold, as the book prefers for detrended series. **Complexity:** low. **Risk:** adds helper surface; keep with unit tests. Not a strategy by itself.

### O5 — Companion-series (intermarket) input for a bot *(book: C4, pp. 391, 437–439 · crypto application is our proposal)*
The divergence family compares a companion series with the traded one. In crypto, BTC is the natural companion for altcoin pairs, and quote-currency pairs (ETH/BTC) are available as spot markets. A strategy parameter `companion_symbol` would need multi-series candles in the strategy context (currently `StrategyContext` carries one candle). Hypothesis **H-COMPANION**, large change; record only.

### Not applicable
US breadth/volume/bond series, long/short reversal rules, S&P 500 specifics.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 geometric grid presets | medium | – | – | very low | – |
| 2 | O3 provenance of parameters | medium | – | – | low | book 3 ch. 6 O2 |
| 3 | O2 practical significance | medium | medium | – | low | metrics |
| 4 | O4 indicator helpers | low | – | – | low | book 2 ch. 3 O1 |
| 5 | O5 companion series | – | – | – | high | H-COMPANION |

## 5. Affected files
App sweep form (`routes/backtests/new`, `components/backtests`), `backtesting/application/service.py` (optional helper and `source` field), `analytics/domain`, `strategies/domain/` helpers, `docs/openapi.json`, tests.

## 6. Incremental plan
1. Geometric grid generator and preset.
2. `source` field and universe count.
3. Practical-significance thresholds with display.
4. Indicator helpers when the mean-reversion strategy is built.

## 7. Acceptance criteria and tests
* The generator reproduces 3, 5, 8, 12, 18, 27, 41, 61, 91, 137, 205 (± rounding) from the stated ratio.
* No change to existing sweeps' behaviour unless the new options are used; ruff, mypy, tests green.

## Caveats
Everything above depends on a single study on one index; the book states that none of the 6,402 rules was significant after correction (see ch. 9). The grid ratio of 1.5 is the author's design choice.
