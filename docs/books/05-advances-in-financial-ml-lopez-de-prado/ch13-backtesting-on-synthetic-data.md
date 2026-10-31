# Book 5 · Chapter 13 — Backtesting on Synthetic Data

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 169–176 (motivation, trading rules, overfit definition, O-U framework, the five-step algorithm and code) and pp. 188–192 (conclusion and exercises) were read. The heat-map figures and their descriptions for each parameter combination (pp. 176–188) were skimmed: the text only narrates how the optimal region moves with half-life and equilibrium, no table of numbers.

**Scope note:** despite the title, the chapter is about **calibrating exit rules (profit-taking and stop-loss) from a fitted stochastic process by Monte Carlo instead of a historical backtest**. It does not provide a general synthetic-market generator for validating entry signals.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Use history to **estimate a stochastic process** and generate many synthetic datasets with the same statistical characteristics, so a strategy is not fit to one path. Focus: **trading rules** (entry/exit tactics): enter when the signal reaches a value; exit by thresholds for profit-taking and stop-loss. Parameters calibrated by historical simulation overfit the in-sample path ("the strategy becomes so attached to the past that it becomes unfit for the future"). | Exit-rule overfitting. | 169–170 |
| C2 | **Formalisation**: opportunity `i` with position `m_i`, mark-to-market PnL `π_{i,t} = m_i(P_{i,t} − P_{i,0})`; a trading rule `R = {π̲, π̄}` exits on the first of profit-taking `π̄` or stop-loss `π̲` (plus a maximum holding period = the vertical barrier of ch. 3); brute-force calibration maximises `SR_R = E[π_{i,T_i}|R] / σ[π_{i,T_i}|R]` over a set of candidate rules `Ω`. With two free variables on a sample of size `I`, overfitting is trivial (a pair that targets a few outliers). **Overfit trading rule**: the in-sample optimal rule is expected to underperform the median of alternatives out-of-sample (same definition as PBO, ch. 11). | Define the problem. | 170–172 |
| C3 | **Framework**: assume the position's price follows a discrete **Ornstein–Uhlenbeck (O-U)** process `P_t = (1−φ)·E₀[P_T] + φ·P_{t−1} + σ·ε_t`, `ε ~ N(0,1)`; stationary iff `φ ∈ (−1, 1)`; `φ = 2^(−1/τ)` where `τ` is the half-life. Question: can the optimal pair `(π̲, π̄)` be derived from `{φ, σ}` and the initial conditions **without a historical simulation**? | Model for mean-reverting positions. | 172 |
| C4 | **Five-step algorithm**: (1) estimate `φ` and `σ` by OLS on the linearised equation (13.5); (2) build a mesh of `(π̲, π̄)` pairs (e.g. 20×20, multiples of σ from 0.5 to 10); (3) simulate many paths (e.g. 100,000) per opportunity with a maximum holding period (e.g. 100); (4) apply each rule to each path and compute the Sharpe ratio per node; (5) pick the optimal pair, or the optimal stop-loss given a profit target (5b), or the optimal profit-taking given a maximum stop-loss (5c). Code (Snippets 13.1–13.2) with `forecast ∈ {10, 5, 0, −5, −10}`, `half-life ∈ {5, 10, 25, 50, 100}`, `σ = 1`, `maxHP = 100`, `nIter = 1e5`. | Algorithm. | 173–176 |
| C5 | **Experimental results** (heat maps of Sharpe ratio on the profit/stop mesh): zero long-run equilibrium (market-maker-like), positive equilibrium (position-taker; optimal profit-taking larger), negative equilibrium (mirror image). As the half-life grows the process approaches a random walk, the region of best performance spreads and the Sharpe falls (e.g. Sharpe ≈ 12 for forecast 5, half-life 5 in one figure); the optimal rule depends on `{E₀[P_T], τ, σ}`. | Behaviour of optimal rules. | 176–188 |
| C6 | **Conclusion and conjecture**: for O-U prices there is a **unique optimal combination** of profit-taking and stop-loss that maximises the Sharpe; the author argues the probability that the conjecture is false is negligible compared with the probability you will overfit by ignoring it, so "assume it is right and determine the OTR through synthetic data; in the worst case it is suboptimal but will outperform an overfit trading rule". (No proof; the claim rests on the experiments shown.) | Takeaway. | 192 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Stop-loss and take-profit parameters calibrated by historical sweeps | ✅ | Stops/targets are strategy/risk parameters; sweeps can include them (subject to the book 4 caveat that the stop value matters less than the entry rule). |
| Maximum holding period | ❌ | None (ch. 3 O2). |
| Estimation of mean reversion parameters (half-life) | ❌ | None (book 2 ch. 2 covers half-life; not implemented). |
| Synthetic path generator | ❌ | Seeds exist for deterministic backtests, but no synthetic price generator. |
| Exit-rule evaluation independent of the historical path | ❌ | — |

## 3. Opportunities

### O1 — Synthetic-path sanity test bed (null models) for the evidence pipeline *(book: C1, C4 · generalisation, ours)*
* **Proposal:** a deterministic generator of synthetic price series with controlled properties: (a) driftless Gaussian random walk (null), (b) random walk with volatility clustering (GARCH-like or regime-switching volatility), (c) O-U with chosen half-life, (d) trending process with planted drift; parameters can be estimated from a real series (match mean, volatility, autocorrelation, kurtosis). Use them to (i) unit-test that strategies and the sweep/PBO machinery behave as expected (no edge → no significant results, planted edge → detected), and (ii) provide a **null distribution** of the best sweep result under "no edge but same volatility" (the permutation/bootstrap of book 3 done parametrically).
* **Why:** answers directly the question "what would the best-of-N be if there were no edge?" and doubles as the validation of every proposed statistic (PBO, deflated Sharpe, CPCV). The book's algorithm is the template (simulate many paths from a fitted process, evaluate every rule on each).
* **Complexity:** medium (generators + seeded runner + comparison); computational cost = number of paths × sweep size (reduce with vectorised evaluations). **Risks:** results depend on the process specification; a Gaussian null underestimates fat tails and volatility clustering; use bootstrap/regime nulls too. **Validation:** generators reproduce target moments; same seed same path; the null distribution of best-of-N Sharpe grows with N as predicted by the expected-maximum formula (ch. 14).

### O2 — Mean-reversion diagnostics and half-life estimation (feeds exit design for mean-reversion strategies) *(book: C3, C4 steps 1, p. 173)*
Estimate `φ` by OLS regression of `P_t − m` on `P_{t−1} − m` (equivalently the AR(1) coefficient on the deviation from the equilibrium or from a moving average), derive half-life `τ = −ln 2 / ln φ`, volatility `σ`, and show in the series diagnostics (with confidence intervals and a stationarity warning when `|φ| ≥ 1`). Overlaps with Chan (book 2 ch. 2: half-life of mean reversion via Ornstein-Uhlenbeck regression) — implement once. Required if a mean-reversion strategy is added. **Complexity:** low. **Validation:** simulated O-U with known `φ` is recovered.

### O3 — Profit-taking/stop-loss grid evaluated on simulated O-U paths for a mean-reversion strategy (only if such a strategy is built) *(book: C4, C5, pp. 173–188)*
Reproduce the book's mesh: for a mean-reversion strategy with estimated `{φ, σ}`, compute the Sharpe heat map of `(stop, target)` (multiples of σ) on 10⁴–10⁵ simulated paths with a maximum holding period; compare to the heat map obtained by historical simulation and report the overlap. Use it as a prior, not as truth: crypto spot prices are not O-U in general (trending, jumps), so the estimated `φ` should be validated (ADF/half-life stable across subperiods) before using the result. For **trend-following** strategies (current ones) this procedure is inappropriate because the O-U assumption contradicts the premise. **Complexity:** medium; tied to a future mean-reversion strategy. **Risks:** model misspecification (jumps, fat tails, volatility clustering) makes the "optimal" corridor optimal for a world that does not exist; present as a regularising prior on exits. **Validation:** against analytic checks on degenerate cases (φ = 0: i.i.d. noise around equilibrium), symmetric forecasts mirror (the book notes mirror images for ±forecast).

### O4 — Hold the book's conjecture lightly: do not rely on a single "optimal" exit pair *(book: C6, p. 192)*
The unique-optimum conjecture is empirical and bounded to the O-U model. Our own plateau/neighbourhood approach (book 4 ch. 21) and PBO are consistent with it as a regulariser; but we should not hard-code "optimal" corridors. Record in the research docs: exits are chosen on a plateau of the simulated and historical heat maps, and the corridor must survive costs and gaps. **Complexity:** none.

### Not applicable
Execution-trader exercises (covering a short with specified exits), the Python 2 style code, the multiprocessing exercise (ch. 20 of the book).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 synthetic null/test bed | very high | – | – | medium | ledger/PBO/DSR work |
| 2 | O2 half-life/mean-reversion diagnostics | medium | – | – | low | diagnostics module |
| 3 | O3 simulated exit corridor (mean-reversion only) | medium | medium | – | medium | a mean-reversion strategy |
| 4 | O4 documentation | low | – | – | doc | – |

## 5. Affected files
`analytics/domain/` (synthetic generators, null distribution runner, half-life estimator), `backtesting/application` (run a strategy on synthetic datasets with stored seeds), tests, docs; app diagnostics.

## 6. Incremental plan
1. Random-walk and O-U generators with moment tests.
2. Null distribution of best-of-N for a sweep (feeds PBO/DSR validation).
3. Half-life diagnostics; later the exit-corridor heat map.

## 7. Acceptance criteria and tests
* Generators: sample moments within tolerance; reproducible by seed; O-U half-life recovered by OLS within confidence interval.
* Null distribution: with no edge, the mean of the best Sharpe over N trials increases with N and the fraction of runs above a significance threshold matches the nominal rate after correction.
* ruff, mypy, existing tests green.

## Caveats
The "optimal trading rule" results are for a *known* O-U process; real prices deviate, so the corridor is only as good as the model. The conjecture is unproven. The chapter's heat maps are illustrative (specific parameter combinations), the Sharpe values depend on `σ` and holding limit, and the chapter does not test any real strategy on real data. The title "Backtesting on Synthetic Data" promises more than what is delivered here (the general synthetic-data backtest of entry signals is not covered).
