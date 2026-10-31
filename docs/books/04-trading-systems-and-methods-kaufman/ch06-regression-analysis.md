# Book 4 · Chapter 6 — Regression Analysis

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 235–237, 257–259 and 273–276 were read. The mathematics of simple and multiple regression, nonlinear fits, ARIMA and Kalman filtering (pp. 238–256, 259–272), and "Measuring Market Strength" (pp. 276–278) were **not** read and are not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | A price series has a **trend**, a **seasonal/cyclic** component and an unexplained **random** remainder; regression isolates the trend; short trends (days/weeks) cannot be explained by macro factors and are mostly investor reaction to news flow. Avoid erroneous relationships: "a sound premise is the basis for success". | What regression is for. | 235–236 |
| C2 | Lower-frequency data smooths the series (extremes rarely fall on the last day of the month); the **calculation period** should not equal a cycle length that would average itself out (a 12-month window around a seasonal cycle neutralises it). | Window choice. | 236–237 |
| C3 | Log and exponential fits turn nonlinear relationships into linear least squares by transforming variables; the best statistical fit (smallest error standard deviation) is **not necessarily the best forecast**: the worst-fitting logarithmic model gave the most realistic soybean forecast; show system performance with fixed investment on a **log scale**; re-estimate models on a rolling window. | Fit vs forecast. | 257–258 |
| C4 | **Regression trading rule (similar to a moving average)**: an n-day linear regression of closes gives a forecast `F_{t+1}`; buy when tomorrow's close exceeds the forecast, sell short when below; to avoid whipsaws add **confidence bands** around the line: 90% = 1.65 and 95% = 1.96 (usually 2.0) times the standard deviation of the residuals; the regression signals a change of direction **sooner than a moving average**, which has a lag acting as a safety zone; performance tends to improve with longer periods. | Objective trend rule with a band. | 273–274 |
| C5 | **Slope rule**: buy when the regression slope is positive, sell when negative; the slope is on a different scale from price (separate panel); competitive with other trend methods (Chapter 8). The slope can be misleading: the same slope arises from smooth or very noisy moves, so add the **correlation R between price and a sequence of integers** (not R², so the sign shows direction); slope is faster than a moving average but less stable; adding R gives complementary information. | Trend direction and consistency. | 275–276 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Regression-based trend rules | ❌ | Not in the catalogue; no regression helper. |
| Trend-quality measure (R) as filter | ❌ | None (also the efficiency ratio, book 4 ch. 1 O1). |
| Confidence band from residual deviation | ❌ | None. |
| Rolling re-estimation | ✅ | Strategies compute indicators only on past candles. |
| Log-scale display of fixed-size equity | ⚠️ | The app's equity chart scale not verified here. |

## 3. Opportunities

### O1 — Trend-quality filters as optional entry conditions *(book: C5, p. 275–276; combined with ER from book 4 ch. 1)*
* **Problem:** trend strategies (EMA cross, Donchian) trade the sideways noise that the book describes; a measure of how consistent the trend is could skip low-quality entries.
* **Proposal:** two candidate quality measures computed over a window: the correlation `R` of closes against a time index (sign = direction, magnitude = consistency) and the efficiency ratio (book 4 ch. 1). Add an optional parameter such as `min_trend_quality` to the trend strategies: enter only if the measure exceeds the threshold. Default off.
* **Benefit:** a hypothesis about reducing whipsaw trades without adding a new strategy. **Complexity:** low–medium (helpers, one parameter, tests).
* **Risks:** more parameters and filters → overfitting (the author warns that too many filters lead to overfitting or no trades, ch. 1); the filter delays entries (lag); no performance numbers are given in the pages read. Treat as **H-TREND-QUALITY** and test only through the sweep → best-of-N → validation pipeline with the extra parameter counted in N. **Validation:** truncation test; effect on trade count and drawdown; sensitivity.

### O2 — Regression slope strategy (with R) as a new trend family *(book: C4, C5, pp. 273–276)*
* **Proposal:** buy when the n-bar regression slope of closes is positive (optionally with a residual-based band, 1.65/1.96/2.0 multipliers, or with R above a threshold), sell when it turns negative or falls below the band. It is related to book 4 ch. 4 O1 (regression channel) and should be implemented as one strategy covering both ideas with explicit modes, not two near-duplicates (the duplicates would inflate N without information, book 3 ch. 6 O4).
* **Benefit:** faster response than a moving average (the author's point) with a quality gauge. **Complexity:** medium. **Risks:** the faster response means more false signals and higher costs; the book says performance "tends to improve as the calculation period increases", i.e. long windows are preferred, which for crypto must be tested. **Validation:** as above.

### O3 — Verify the equity chart's scale handling *(book: C3, p. 257)*
Check the app's equity/underwater charts: for fixed-fraction systems the log scale is the honest view; if the chart is linear, offer a log-scale toggle (lost-ui chart request L-n). **Complexity:** low (frontend), subject to the chart library's capabilities (the earlier project notes mention the equity chart's y-axis starting at 0 as a lost-ui limitation).

### Not applicable
Nonlinear least squares, multivariate regression, ARIMA, Kalman filter (see book 2 ch. 3 for the filter in the context of mean reversion), market strength rankings.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 chart scale check | – | – | low | low | lost-ui capabilities |
| 2 | O1 trend-quality filter | medium | – | – | low–medium | helpers; pipeline |
| 3 | O2 regression slope strategy | medium | – | – | medium | helpers; pipeline |

## 5. Affected files
`strategies/domain/` (helpers, optional parameter, new strategy), catalogue and forms, app chart components (`equity-chart-rows.ts`), tests including the truncation test.

## 6. Incremental plan
1. Helpers (linear regression slope, R, residual deviation, ER) with unit tests.
2. Filter option on the existing trend strategies.
3. Regression strategy after the pipeline is in place.

## 7. Acceptance criteria and tests
* Regression helpers reproduce hand-computed slopes, correlations and residual deviations; degenerate windows return `None` or no signal.
* New parameters are optional; defaults leave current strategies unchanged; ruff, mypy, tests green.

## Caveats
Most of the chapter (statistical derivations and examples with commodities and stocks) was not read. The statements about performance improving with longer windows come from futures tests in the book and may not hold for crypto.
