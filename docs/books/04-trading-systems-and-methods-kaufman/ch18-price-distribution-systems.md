# Book 4 · Chapter 18 — Price Distribution Systems

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** only pp. 801–802 (introduction and volatility measurement) were read. The sections "Use of Price Distributions and Patterns to Anticipate Moves" (805–810), "Distribution of Prices" (811–821), "Steidlmayer's Market Profile" (822–829) and "Using Daily Distributions to Identify Support and Resistance" (830–832) were **not** read; their headings and one table of profile letters were seen. This report is therefore short and its opportunities are tentative.

## 1. Chapter summary (what was read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Prices can be viewed as a **distribution** instead of a time series (options pricing compares historic and implied volatility; risk managers use annualised standard deviation). The standard deviation is the basic measure: ±1σ ≈ 68% of movement, ±2σ ≈ 95%, ±3σ ≈ 99.7%; theoretically all within ±3.5σ. | 801 |
| C2 | **Measuring distribution needs enough data**, and volatility is compared over **20-day windows** to see changes; crude oil annualised volatility was 39% over 1983–2010 but spiked to 140% at the end of 2008 (a downward move can never exceed 100% while the standard deviation of returns includes upside swings from $30 to $150 and back); volatility can spike for short periods under extreme stress. | 801–802 |
| C3 | (Not read) Market Profile (Steidlmayer) builds a distribution of time or volume at each price level during the session to find value areas and support/resistance. | 822–832 (headings only) |

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| Rolling realised volatility | ❌ | Not computed anywhere (no volatility metric in `analytics`). |
| Price-level distribution (volume or time at price) | ❌ | None. |
| Annualised volatility of a bot's returns | ❌ | Not in `Metrics` (book 4 ch. 2 O1). |

## 3. Opportunities

### O1 — Rolling realised volatility as a shared feature and display *(book: C1, C2, pp. 801–802)*
The 20-bar (configurable) annualised realised volatility, with the convention of book 1 ch. 3 O1 (365 days for crypto), is a prerequisite for ATR/σ-based stops and sizing (ch. 20, 23), volatility targeting (ch. 2 O4) and shock ratios (ch. 14 O1). One implementation; display next to the candle chart. **Complexity:** low. **Caveat from the book:** realised volatility computed from returns reflects both directions; large upward moves raise it as much as crashes; for risk use downside or drawdown-based measures too (ch. 2 O1).

### O2 — Volume-at-price profile (value area, point of control) as a research diagnostic only *(book: C3 · idea only, chapter not read)*
Candle OHLCV allows an approximate volume profile (spread each candle's volume over its range) from which a point of control and value area can be computed. Whether these levels act as support/resistance in crypto is an empirical question; any such study must be conducted as the diagnostics-and-pipeline process in book 3 (objective definition, out-of-sample, multiple-testing counts). **Complexity:** medium. Recorded as **H-VOLUME-PROFILE**; **not recommended before reading the chapter**.

### Not applicable
Options-implied volatility, Market Profile letter charts.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 realised volatility feature | medium | medium | – | low | – |
| 2 | O2 volume profile | low | – | – | medium | reading the chapter |

## 5–7. Files, plan, acceptance
`analytics/domain/` (rolling volatility), shared with strategies helpers; app chart display. Acceptance: matches hand-computed volatility on fixtures; scale-invariant; ruff, mypy, tests green.

## Caveats
The chapter's main content (distribution-based systems and Market Profile) was not read. The only quantitative claim read is the volatility spike example from crude oil.
