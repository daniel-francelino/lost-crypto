# Book 4 · Chapter 7 — Time-Based Trend Calculations

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 279–281 and 293–304 were read. The sections on the simple moving average and its variants (pp. 281–292: weighted, triangular, geometric average) and the end of the chapter on plotting lags and leads (pp. 305–308) were **not** read in detail. EMA, the construct used by the project's `ema_crossover`, is covered in the read part.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | All trend methods remove noise to find direction; there may be several trends at once; **there is no "right" trend, only benefits and compromises**; predictive models degrade when **extrapolating outside the historic range** of values. Distinguish **forecasting** (price with confidence) from **following** (autoregressive evaluation of current direction: up, down or sideways). Trend followers assume past data predicts the future direction. | What a trend filter promises. | 279–280 |
| C2 | **Lag is the zone of uncertainty** that lets the method ignore market noise; effort to reduce lag increases false signals. The best historic results often come from **overfitting**. | Lag vs noise trade-off. | 280 |
| C3 | **Drop-off effect** (abrupt change when an old value leaves a fixed window: `(p_t − p_{t−n})/n`): simple averages, regressions and weighted averages have it; front-weighted and **exponential smoothing** reduce it. Accumulative averages depend on the start date. | Behaviour of window-based filters. | 293 |
| C3b | **Exponential smoothing**: `E_t = E_{t−1} + a·(p_t − E_{t−1})`, started with `E₁ = p₁`; developed in WWII for tracking; the conversion from days is `a = 2/(n+1)` (Hutson), which ignores the lag; a general residual-impact formula `c = 1 − RI^{1/n}`; with `2/(n+1)` the residual impact of old data is a **consistent 13–14%**. | EMA definition and equivalence. | 293–298 |
| C4 | **EMA vs simple moving average**: not equivalent: the exponential never discards old data, so a "10%" smoothing is slower than a 10-day MA; in a steady ramp the 5-day MA settles at a constant lag of 1 while the 20% EMA only approaches it, and **changes direction one period later** after a peak. | Why EMA and SMA signals differ. | 298–299 |
| C5 | **Test distribution**: if smoothing constants are spaced equally, half the tests are averages of three days or less; **equally spaced smoothing constants are a better test distribution than equally spaced days**; the relation constant ↔ days is close to logarithmic. | Parameter grids for optimisation. | 299–301 |
| C6 | **Reducing lag / smoothing**: error-corrected smoothing (smooth the lag `e_t = p_t − E_t`, add it back; the corrected line sits mid-move, "a good candidate for mean reversion"); **double smoothing** slows the line and gives triangular-like weights; Blau's **double smoothing of price changes (momentum)** restores speed, with long first smoothing and short second (e.g. 250/5), but the result is not on the price scale. | Lag reduction techniques. | 301–304 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| EMA definition | ✅ | `ema_crossover.py`: `alpha = 2/(period+1)`, seeded with the **SMA of the first `period` closes**, then updated incrementally. (The book seeds `E₁ = p₁`; both are standard, seeding differs only for the early warm-up.) |
| Warm-up handling | ✅ | No signal during warm-up and on the candle where it completes (documented in the module). |
| Fixed-window drop-off | n/a | EMA only. |
| Smoothing constant grids | ⚠️ | The strategy takes integer periods; sweeps with linear integer grids are dense at slow periods and sparse at fast ones. |
| Lag as a reported characteristic | ❌ | Not reported anywhere. |
| Error-corrected / double smoothing / Blau momentum | ❌ | None. |
| Out-of-range extrapolation caution | n/a | No forecasts. |

## 3. Opportunities

### O1 — Log-spaced grids for periods (confirms Aronson's ×1.5 spacing) *(book: C5, pp. 299–301)*
Kaufman's argument (equal steps in smoothing constants beat equal steps in days; the relation is near logarithmic) supports the geometric grid already proposed (book 3 ch. 8 O1). Add that justification to the sweep helper's documentation, and make the generator offer both views (periods or smoothing constants). **Complexity:** very low.

### O2 — Report the expected lag of each trend filter *(book: C2, C4, pp. 280, 298–299)*
Show an approximate lag for the configured fast and slow EMAs and the effective residual impact, so users understand the speed/noise trade-off when choosing periods. For a steady ramp of one price unit per bar, an EMA with constant `a` trails the price by `(1−a)/a` price units in steady state, i.e. 4 for `a = 0.2` (a standard result derived from the definition, not stated in this form in the book). It is consistent with Table 7.7: with prices rising by 1 per bar the 20% EMA is 3.83 below the price at the 15th point and approaches 4. Treat the closed form as ours and unit-test it against that table. **Complexity:** very low (display).

### O3 — Allow the smoothing constant directly for sweeps *(book: C3b, C5, pp. 295–301)*
Optional: express the EMA speed as `n` (days) but sweep over `n` produced by a log-spaced generator (O1), instead of adding a new parameter. Low priority; mostly O1.

### O4 — Lag-reduction variants as experiments *(book: C6, pp. 301–304)*
Double smoothing of momentum (Blau) and error-corrected EMA are objective, parameterised indicators. They add parameters (two smoothing spans) and complexity; the author warns that the best historic results often come from overfitting. Record as **H-LAG-REDUCTION**; test only after the evidence pipeline and with their parameters counted in N. **Complexity:** medium.

### Not applicable
Accumulative averages, geometric averages, plotting lags and leads (not read).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 log-spaced grids | medium | – | – | very low | book 3 ch. 8 O1 |
| 2 | O2 lag display | low | – | – | very low | – |
| 3 | O3 constant-based sweeps | low | – | – | low | O1 |
| 4 | O4 lag-reduction variants | low | – | – | medium | pipeline |

## 5. Affected files
App sweep form and helper; `strategies/domain/ema_crossover.py` only for displays; docs; tests.

## 6. Incremental plan
1. Document the grid rationale; ship the generator.
2. Add the lag/residual-impact hint to the strategy form.
3. Experiments only through the pipeline.

## 7. Acceptance criteria and tests
* Tests for the grid generator and, for O2, a unit test comparing computed lag against Table 7.7's 20% EMA values.
* No change to existing strategies; ruff, mypy, tests green.

## Caveats
The numbers (13–14% residual impact, smoothing equivalents) are mathematical properties of the EMA definition and hold generally; statements about test distributions are the author's practical advice. In O2 the closed-form lag expression is ours (checked only against Table 7.7).
