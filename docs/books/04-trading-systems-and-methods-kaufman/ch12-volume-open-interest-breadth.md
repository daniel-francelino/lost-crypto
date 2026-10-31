# Book 4 · Chapter 12 — Volume, Open Interest, and Breadth

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 527–530 and 554–558 were read; the headings of 536–553 and 559–564 were scanned. The volume-indicator catalogue (on-balance volume, accumulation indexes, breadth indicators, pp. 535–553), the intraday-volume and filtering sections (559–564) were **not** read in detail and are not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Volume is one of the few data items besides price traditionally valid for technicians; little research exists for futures. **Breadth** (advancing vs declining stocks, new highs/lows) and **open interest** are related participation measures; futures have contract-specific volume that rises as a contract nears the front month; use **total volume** across contracts for analysis; **tick volume** (number of price changes) approximates volume when real volume is not available. | Volume data and its quirks. | 527–529 |
| C2 | **The W intraday pattern**: volume is high at the open, drops, rises modestly midday, falls, and rises into the close; so **intraday volume confirmation must be compared with the normal volume for that time of day**. Open interest and breadth have seasonal patterns too (no special meaning in themselves). | Misreading volume intraday. | 529 |
| C3 | **Variance in volume**: volume is far more variable than price (Microsoft: standard deviation of daily volume ≈ 38% of the average vs 2.9% for price); analysis uses smoothed or averaged volume. | Noise in volume. | 529–530 |
| C4 | **Volume spikes**: a day with volume at least 2× (perhaps 3–4×) the recent norm; read as crowd behaviour (everyone jumped in) and traditionally as **exhaustion** of the move; examples (AOL, Microsoft bubble end) show spikes at turning points, "though the reversal is not always large". "No comprehensive tests available". Spike detection: `V_t > T × AV_{t−1}`, improved by **lagging the average five days** so that a spike built over 2–3 days is not masked by its own rise: `V_t > T × mean(V_{t−n−5} … V_{t−5})`. | Volume as an extreme-event detector. | 530, 554–555 |
| C5 | **Volume confirms vs signals reversal**: most oscillator approaches say high volume confirms a new direction while *extreme* volume signals reversal; a drop in volume suggests equilibrium and needs further confirmation. | Two uses of volume. | 554 |
| C6 | **Volume confirmation of a trend entry**: require current volume above its 10-day average for a 20-day trend position (Saitta); Waxenberg: confirm a trend change with a 20% volume increase over the 10-day mean and treat about 40% as an extreme, optionally replacing fixed percentages with Bollinger bands (2σ). The filter "eliminates a substantial number of trades"; **if net returns are equal, the volume-filtered version is far better** (less time in the market, less reversing, more liquidity). | Filtering trades with volume. | 556–557 |
| C7 | Breadth systems (Connors–Hayward advance-decline pattern and breadth as a counter-trend indicator) with thresholds that must be rescaled as volatility changes (a 10 bp trigger developed in 1995 now trades daily). | Thresholds drift. | 557–558 |

Futures- and equity-breadth specifics are not applicable. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Volume stored | ✅ | `Candle.volume` is persisted (`market_data/domain/models.py`). |
| Volume used in strategies/risk | ❌ | `StrategyContext` exposes the candle (so volume is accessible) but neither strategy uses it; `RiskLimits` has no volume-based limit (also noted in book 1 ch. 5). |
| Intraday volume pattern normalisation | ❌ | None. |
| Volume spike detection | ❌ | None. |
| Volume confirmation filter | ❌ | None. |
| Which volume | ⚠️ | Candle volume is **per exchange and per symbol**; in crypto, volume can be inflated by wash trading on some venues, and exchange volume is a share of the market (not mentioned in the book). |
| Breadth / open interest | n/a | Spot, single symbol. |

## 3. Opportunities

### O1 — Time-of-day-normalised volume feature (relative volume) *(book: C2, C3, p. 529)*
* **Proposal:** a helper `relative_volume = volume / mean(volume at the same hour-of-day over the last N days)` (and the variant against the previous `n` bars), the basis for all volume rules, so that regular intraday and weekday volume cycles are not mistaken for signals (the W pattern in the book; crypto has its own regional cycles that I have not verified).
* **Benefit:** a correct basis for any volume-based filter or risk rule. **Complexity:** low. **Validation:** synthetic series with a planted intraday cycle must give relative volume ≈ 1 throughout.

### O2 — Volume spike detector and "exhaustion" diagnostics *(book: C4, pp. 530, 554–555)*
* Implement the lagged-average spike test (`V_t > T × mean(V_{t−n−5…t−5})`, `T` = 2 default, `n` configurable) and report, for a symbol/timeframe, the **forward return after spikes** against the unconditional forward return, with sample sizes and eras (book 4 ch. 10 O1 style). This tests the traditional "spike = exhaustion" claim, which the book says has no comprehensive tests. **Complexity:** low–medium. **Risks:** multiple testing (threshold T and horizon); volume in crypto is venue-specific. **Validation:** synthetic series with planted post-spike reversals.

### O3 — Volume-confirmation filter for trend entries (experiment) *(book: C6, pp. 556–557)*
* Optional parameter on the trend strategies: enter only if `relative_volume ≥ x` (or volume above its n-bar average by ≥ 20%, or above a 2σ band). The book's claim is that the filter lowers the trade count and, if returns are equal, reduces risk; test whether it helps in crypto. **H-VOLUME-FILTER**; counted in N; default off. **Complexity:** low–medium. **Validation:** effect on trade count and drawdown through the pipeline; truncation test.

### O4 — Use volume for position-size and liquidity limits *(book: C1, C2; links to book 1 ch. 5 O3)*
The same relative-volume measure can drive the volume-cap limit proposed earlier (order size ≤ a fraction of recent traded volume) and the risk module's suspect-candle logic (an abnormal range on abnormally low volume may be a bad print). **Complexity:** low–medium; part of the risk work.

### Not applicable
Open interest, breadth indicators, delivery-month volume, tick-volume substitutes, equity advance–decline systems.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 relative volume | medium | medium | – | low | – |
| 2 | O4 volume in risk | – | medium | medium | low–medium | O1; book 1 ch. 5 O3 |
| 3 | O2 spike diagnostics | medium | – | – | low–medium | O1; diagnostics module |
| 4 | O3 volume filter experiment | low | – | – | low–medium | O1; pipeline |

## 5. Affected files
`strategies/domain/` (helper), `risk_management/domain/models.py` (optional volume limit), `analytics/domain/`, diagnostics endpoint, app forms, tests including the truncation test.

## 6. Incremental plan
1. Relative-volume helper with tests.
2. Spike diagnostics (read-only).
3. Volume-aware risk limit (optional).
4. Filter experiment through the pipeline.

## 7. Acceptance criteria and tests
* Relative volume is ≈ 1 on a pure intraday-cycle series; spike detector flags planted spikes only; new options default off; ruff, mypy, tests green.

## Caveats
The text itself notes the lack of comprehensive tests for the volume-spike rule and gives no performance numbers for the filters in the pages read. Candle volume from a single exchange may not represent total market activity.
