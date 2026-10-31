# Book 5 · Chapter 5 — Fractionally Differentiated Features

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 75–86 were read (motivation, stationarity vs memory dilemma, literature, fractional differencing method, weights and convergence, expanding window and fixed-width window implementations, minimum d for stationarity, Table 5.1 start). Pages 87–90 (the rest of Table 5.1, conclusions, exercises) were not read.

**Fit with the platform:** the platform has no ML features today. This chapter is only relevant if a model is trained on price-level information (meta-labeling, ch. 3 O3), or for a diagnostic of how much memory raw prices carry. It is a low-priority, future-facing chapter.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Stationarity vs memory dilemma**: supervised models usually need stationary features, but the usual integer differencing (returns) removes **all memory**, while price levels keep memory but are non-stationary. Memory is the basis of predictive power (e.g. equilibrium models need to know how far price drifted from its mean). Stationarity is "necessary, non-sufficient". Question: what is the **minimum differencing that makes the series stationary while preserving as much memory as possible**? Returns are "one kind of (and in most cases suboptimal) transformation". | Over-differencing. | 75–76 |
| C2 | **Fractional differencing**: generalise `(1 − B)^d` to real `d` via the binomial series; `X̃_t = Σ_k ω_k X_{t−k}`, `ω_k = −ω_{k−1}(d − k + 1)/k`, `ω_0 = 1`; `d = 0` returns the original series, `d = 1` the first difference `{1, −1, 0, …}`; for `0 < d < 1` weights are negative, decay and converge to zero (memory is kept with decaying weight). | The transformation. | 76–80 |
| C3 | **Expanding window** applies all weights available and suffers uneven memory among points and a **negative drift** (Figure 5.3) unless weight loss is controlled; **fixed-width window (FFD)** drops weights with `|ω_k| < τ` (e.g. 1e-5), uses the same weight vector for every point, and yields a **driftless blend of level plus noise**; the output is stationary but no longer Gaussian (skew and kurtosis from the memory). | Practical implementation. | 80–84 |
| C4 | **Minimum d**: for the E-mini S&P 500 log-prices (daily, from inception, rolled with the ETF trick) the ADF statistic crosses the 95% critical value (−2.8623) near **d ≈ 0.35**, where the correlation with the original series is still **0.995**; the returns series (d = 1) has ADF −46.9 and correlation 0.03 with the original. Table 5.1 shows **87 liquid futures** all reaching stationarity at **d < 0.6**, some (orange juice, live cattle) with no differencing; "most studies have over-differentiated the series". | Evidence that d = 1 is excessive. | 84–86 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Feature engineering / models | ❌ | None; strategies use price/indicators directly (EMA, Donchian). |
| Stationarity tests (ADF), fractional differencing | ❌ | None. |
| Price-level memory used by strategies | ✅ (implicit) | EMA crossover and Donchian rely on price level history; they are not statistical models and do not need stationarity. |

## 3. Opportunities

### O1 — Fractional differencing (FFD) as a pure function plus a minimum-d diagnostic *(book: C2–C4, pp. 76–86)*
* **Proposal:** implement `ffd(series, d, threshold)` (fixed-width window) and `min_d(series)` (smallest `d` on a grid such that an Augmented Dickey–Fuller test on the FFD series rejects a unit root at 5%, reporting the correlation with the original at that `d`) in the analytics domain; expose in the series diagnostics for log-prices of each imported pair/timeframe. Use decimals or floats consistently with the analytics module conventions (float only inside the module; money values stay `Decimal` at the boundaries).
* **Why:** if a model is ever built on price-based features, the diagnostics answer how much differencing is needed, giving features that are stationary yet retain memory; also a descriptive statistic of "how trending/persistent" an asset is. The evidence in the book is on futures (87 series), not crypto: a platform measurement would test whether the same holds for BTC/ETH/etc.
* **Cost/risks:** needs an ADF implementation (statsmodels is not in the project; implementing ADF correctly is non-trivial; critical values and lag selection matter) → either add a dependency or implement a narrow, tested version; FFD output is not Gaussian; different `d` per asset makes features non-comparable; `τ` and window width are parameters. **Complexity:** medium. **Validation:** `d = 0` returns the series, `d = 1` equals first differences, weights match the recurrence; ADF statistic matches reference values on fixtures (e.g. a random walk fails to reject, white noise rejects); the result of `min_d` on a synthetic AR(1) near unit root is between 0 and 1.

### O2 — Document which indicators already preserve memory and which are stationary, before ML *(book: C1, pp. 75–76 · adaptation)*
A short note in the research docs: raw returns (stationary, memoryless), price level (memory, non-stationary), EMA ratios, distance-to-channel and z-scores (stationary-ish but with partial memory) and fractional differences as a design choice for model inputs. When ML is considered, features should be defined in this vocabulary and tested with the diagnostic. **Complexity:** documentation.

### O3 — Do not add fractional differencing to the rule-based strategies *(book: C1)*
EMA/Donchian rules operate on levels by design; replacing prices with FFD series would change their meaning and add parameters with no evidence of benefit. Recorded to avoid scope creep. **Complexity:** none.

### Not applicable
ETF trick/futures rolls used to build the continuous series (spot only), the 87-futures table as evidence for crypto, Gaussianity restoration, cointegration methods (book 1/2 cover pairs).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O2 vocabulary note | low | – | – | doc | – |
| 2 | O1 FFD + min-d diagnostic | low–medium | – | – | medium | decision on ADF dependency |
| 3 | O3 (non-action) | – | – | – | – | – |

## 5. Affected files
`analytics/domain/` (new `frac_diff` module) and dependencies (ADF), tests with reference values; docs.

## 6. Incremental plan
Not before the ML track (ch. 3 O3) is approved. If done: FFD function with tests → ADF → diagnostic per pair → decide whether any model needs it.

## 7. Acceptance criteria and tests
* Weight recurrence and special cases (`d = 0`, `d = 1`) verified; FFD length and warm-up as specified; ADF reference outputs match published tables on known series; diagnostics are read-only.

## Caveats
Evidence is on futures (ADF-based) and E-mini S&P daily data; stationarity by ADF is a statistical test with low power and sensitivity to specification; the preserved-correlation measure (0.995 at d = 0.35) says only that the series is close to the original, not that it is more predictive. The book itself notes stationarity does not ensure predictive power. No claim is made that fractional differencing improves trading results in these pages.
