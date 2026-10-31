# Book 5 · Chapter 17 — Structural Breaks

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 249–254 were read (motivation, test taxonomy, CUSUM tests, Chow-type Dickey–Fuller, SADF, log vs raw prices, computational cost). Pages 255–262 (sub/super-martingale tests, SADF variants such as QADF/CADF, exercises) were **not** read.

**Fit with the platform:** regime/break detection as a *diagnostic* and as a *filter feature*. Computationally heavy (SADF is O(n²) regressions) and statistically delicate; useful mostly on daily data.

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | **Structural breaks** (e.g. a mean-reverting pattern giving way to momentum) catch most participants off guard; their losses (stop-outs after holding and hoping) are the source of some of the best risk/reward — so measure the *likelihood* of a break and build features on it. | 249 |
| C2 | Two families of tests: **CUSUM tests** (do recursive forecast errors depart from white noise?) and **explosiveness tests** (does the process show exponential growth or collapse — inconsistent with a random walk or stationarity and unsustainable?): right-tail unit-root tests and sub/super-martingale tests. | 249–250 |
| C3 | **Brown–Durbin–Evans CUSUM** on recursive least-squares residuals (needs features `x_t`; arbitrary starting point makes results inconsistent). **Chu–Stinchcombe–White CUSUM on levels** (Homm–Breitung): `S_{n,t} = (y_t − y_n)/(σ̂_t √(t − n))` with `σ̂²_t = (t−1)⁻¹ Σ (Δy_i)²`, under `H₀: β_t = 0` ~ N(0,1); time-dependent one-sided critical value with `b_{0.05} = 4.6` (by Monte Carlo); the reference level `y_n` is arbitrary, so take the supremum over backward windows `S_t = sup_{n∈[1,t]} S_{n,t}`. | 250–251 |
| C4 | **Explosiveness**: multiple-bubble tests are more robust because a bubble–burst–bubble cycle looks stationary to single-bubble tests (bubbles include sell-offs). **Chow-type Dickey–Fuller** (random walk switching to explosive at an unknown break date; test all break dates within a trimmed interval — Andrews; assumes one break and a bubble lasting to the end of the sample). **Supremum Augmented Dickey–Fuller (SADF, Phillips–Wu–Yu)**: at each end point `t`, run ADF regressions on all start points `t₀ ∈ [1, t − τ]` and take the supremum of the ADF statistics; no assumption on number of regimes; the SADF series spikes in bubble-like behaviour and returns to low levels after the burst (Figure 17.1, E-mini S&P 500). | 251–253 |
| C5 | **Use log prices** for SADF/ADF: on raw prices a rejected unit root implies finite price variance and therefore return volatility falling as prices rise (structural heteroscedasticity); with log prices, scaling `x = k·y` shifts the level by a constant, which matters across decades and bubbles. | 253–254 |
| C6 | **Computational cost**: the nested loop is Θ(n²); for 356,631 dollar bars of E-mini S&P with 3 regressors one SADF update needs about 2.035 TFLOPs and a full SADF series about 242 PFLOPs; HPC parallelisation (ch. 20) is needed at that scale. | 254 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Regime/break detection | ❌ | None; strategies are always on. |
| CUSUM filter (event) | ❌ | Proposed in ch. 2 O3. |
| ADF/unit-root machinery | ❌ | Proposed in ch. 5 O1. |
| Performance decay detection | ❌ | Book 4 ch. 21 O9, ch. 23 O8 propose monitors. |

## 3. Opportunities

### O1 — CUSUM-on-levels break statistic as a cheap diagnostic *(book: C3, p. 251)*
Implement the Chu–Stinchcombe–White statistic `S_t = sup_n S_{n,t}` on log prices (windows limited to a maximum lookback to keep it O(n·L)), plus the critical value `b = 4.6`-based bound as documented (verify the exact time-dependent boundary formula in the book/paper before use — it was not legible in the extraction); show on the chart as a "break likelihood" band. Use for research only: does a break signal precede changes in a trend strategy's hit rate? **Complexity:** low–medium. **Risks:** many false alarms in volatile crypto; arbitrary window. **Validation:** random walk rarely exceeds the boundary; a planted trend change triggers it; deterministic.

### O2 — SADF-style explosiveness indicator on daily log prices (research feature) *(book: C4, C5, pp. 252–254)*
Compute SADF on daily log prices of imported assets with a limited set of start points (stride) and a maximum window to cap cost, requiring an ADF implementation (ch. 5 O1). Use as a **regime feature**: high values = bubble-like run-up (trend strategies thrive, then suffer on collapse); evaluate in backtests whether conditioning entries/sizing on it improves risk-adjusted results (**H-SADF-REGIME**). **Cost:** with daily data (thousands of points) a strided version is cheap; with intraday bars it is not (C6). **Complexity:** medium–high. **Risks:** low power, lookback sensitivity, look-ahead if the supremum is not strictly causal (compute only with data up to `t`); regressions with overlapping windows are dependent. **Validation:** simulated bubble series (explosive AR(1) segment) detected; random walk gives low values; truncation test.

### O3 — Break-aware retraining/re-validation trigger *(book: C1, p. 249 · links to book 4 ch. 21 O9, ch. 23 O8)*
Treat a detected break in the traded asset's dynamics (e.g. realised volatility regime change, CUSUM exceedance) as a trigger to re-check a strategy's expectation sheet and, in the lifecycle (ch. 1 O1), to flag "validity of past evidence in doubt". **Complexity:** low–medium once O1 exists. Notify only (via the alerting module), never auto-stop.

### Not applicable
Brown–Durbin–Evans test (needs a feature model), Chow-type test with an assumed single break, sub/super-martingale tests (not read), HPC strategies for full SADF over dollar bars.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 CUSUM levels diagnostic | low–medium | low | – | low–medium | — |
| 2 | O3 re-validation trigger | – | medium | medium | low–medium | alerts, O1 |
| 3 | O2 SADF regime feature | medium | – | – | medium–high | ADF (ch. 5 O1) |

## 5. Affected files
`analytics/domain/` (break statistics, ADF), diagnostics endpoint/page, tests.

## 6. Incremental plan
O1 first; O2 only if O1 shows information value; link to lifecycle monitors later.

## 7. Acceptance criteria and tests
Statistics reproduce known behaviour on simulated random walks, level shifts, explosive segments; strict causality (truncation test); runtime bounded by configured window/stride; ruff, mypy, existing tests green.

## Caveats
Break tests have low power and high false-alarm rates; thresholds come from simulation under idealised assumptions (Gaussian IID increments). The book offers no evidence that conditioning strategies on these statistics improves performance in the pages read ("some of the best risk/reward" is asserted). SADF's cost is prohibitive on high-frequency bars. Pages 255–262 were not read.
