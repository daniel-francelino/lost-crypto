# Book 4 · Chapter 10 — Seasonality and Calendar Patterns

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 427–436 (framing, data caveats, decomposition, detrending) and pp. 478–483 (stock-market calendar effects) were read. The long middle (pp. 436–477: computing seasonal averages and medians, indexes, seasonal filters, commodity examples) was **not** read in detail and is not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Seasonality is a **yearly cycle tied to real causes** (planting/harvest, demand for energy, travel). Even when not visible, consistent factors remain (harvest-time selling pressure, storage costs in forward prices). Seasonal patterns can bias position size, flag changes in risk, affect direction and be exploited. Structural changes (globalised supply) shift patterns. | Why calendar effects exist. | 427–428 |
| C2 | Seasonal patterns are easier to find than longer cycles because they repeat each calendar year; study with **monthly data** (shorter periods = more noise); start the year at a neutral calendar point if the season start is unknown. | Method. | 429–430 |
| C3 | **Data caveats**: continuous back-adjusted futures cannot be expressed in percentages and differ from cash prices (wheat 1965 $1.72 cash vs $12.45 back-adjusted); stock splits alter old percentages; seasonal studies use cash prices where possible. | Data quality for seasonal analysis. | 430 |
| C4 | **Seasonal decomposition / detrending**: separate trend, seasonal, cycle, noise (software options for seasonal differences with period 12 for monthly data and about 252 for daily); detrend by regression and take residuals; because the trend is a constant monthly drift it does not change the seasonal shape. | Isolating the seasonal component. | 430–431 |
| C5 | **Stock market calendar effects**: patterns **changed** between 1982–2000 and later years (the S&P's summer weakness and the "buy in May and go away" adage no longer reliably hold; October–November strength persisted); "only the most significant patterns will survive". **Holiday effect** (Merrill, Fosback): day before holidays up 67.9% of the time (1897–1964) vs a ~54% general up-day rate; Fosback's holiday strategy returned 880% in 1928–1975 with 70% winners and only a few days of exposure per year, but Freeburg found it still profitable but less impressive. **Month-end effect**, **January effect / January barometer** (patterns table; in the 12 years to 2010 only 7 correct, net 14 points: "still a confirmation, but very weak. Geopolitical events can overwhelm these patterns"); McGinley's January rule with a chi-squared of 8–82 in the table (extraction is garbled). | Calendar effects and their decay. | 478–483 |

Examples are futures and US stocks. Crypto has no harvest cycle or exchange holidays. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Calendar/time features available to strategies | ❌ | `StrategyContext` carries a single closed candle and the position quantity; no explicit calendar features beyond `candle.open_time` (which does exist). |
| Seasonal decomposition / detrended seasonal analysis | ❌ | Not in diagnostics. |
| Persistence check across sub-periods | ❌ | No sub-period comparison (book 1 ch. 2 O5, book 2 ch. 5 O1). |
| Risk handling of structural change in a pattern | ❌ | None. |

## 3. Opportunities

### O1 — Calendar-effect diagnostics with persistence checks (research tool) *(book: C2, C4, C5, pp. 430–431, 478–479)*
* **Problem:** crypto traders often assume weekday/month/hour effects; the book's own S&P example shows effects that appear in one era and vanish in the next.
* **Proposal:** extend the diagnostics module (book 2 ch. 2 O1; book 2 ch. 4 O3) with detrended mean and median returns by **hour of day (UTC), day of week and day of month**, computed separately for **two or more eras** (first half vs second half, or per year) with sample sizes, so that persistence across eras is visible, as in the book's 19-year vs 10-year comparison. Use returns (crypto spot has percentages, unlike back-adjusted futures) and detrend by subtracting the sample mean (book 3 ch. 1).
* **Benefit:** a cheap, honest look at whether any calendar structure exists and whether it persisted. **Complexity:** low–medium (pure aggregation).
* **Risks:** data mining across 24×7×(per-pair) buckets (state the number of buckets examined and apply the best-of-N logic, book 3 ch. 6); weekly/hourly patterns in crypto mostly reflect volume cycles of regions; effect sizes are small relative to costs. **Validation:** synthetic data with a planted hour effect; null data produce spurious buckets at the expected rate (about 5% at p = 0.05 before correction).

### O2 — Time-window filter for existing strategies (experiment only) *(book: C1, C5, pp. 428, 479–480)*
If O1 shows a persistent window, add an optional "allowed hours/weekdays" filter to a strategy as an experiment, with its parameters counted in N. The holiday-effect example shows how a rule with tiny exposure can dominate returns, which is exactly the pattern that is easy to overfit. **H-CALENDAR-WINDOW**; do not implement without evidence from O1 that survives the pipeline. **Complexity:** low.

### O3 — Treat known scheduled events as exposure-control inputs *(book: C1, p. 428 · adaptation)*
The book lists seasonal factors as inputs for sizing and risk changes. A crypto analogue is scheduled events (token unlocks, protocol upgrades, exchange maintenance, major macro dates). The system has no event calendar (also B-EVENTS in book 2 ch. 7). Record only; if built, use for **risk reduction or pausing**, not for return prediction.

### Not applicable
Agricultural crop-year methods, cash vs futures, holiday effects tied to exchange holidays, January/barometer rules.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 calendar diagnostics | low–medium | – | – | low–medium | diagnostics module |
| 2 | O2 window filter | low | – | – | low | evidence from O1 |
| 3 | O3 event calendar | – | medium | – | medium | B-EVENTS |

## 5. Affected files
`analytics/domain/` (grouped aggregation), `market_data/presentation/router.py`, app market-data diagnostics, tests.

## 6. Incremental plan
1. Aggregation functions with synthetic tests.
2. Era split and bucket counts displayed with every table.
3. Filter experiment only if a persistent effect survives out-of-sample testing.

## 7. Acceptance criteria and tests
* Aggregations match hand computations; every cell shows its sample size and the number of cells examined.
* Diagnostics are read-only; no trading behaviour changes; ruff, mypy, tests green.

## Caveats
The holiday and January results are for US stocks across many decades and the author himself says they weakened. They give no support for any calendar effect in crypto. The garbled table on p. 483 (extraction of McGinley's results) was not interpreted.
