# Book 5 · Chapter 9 — Hyper-Parameter Tuning with Cross-Validation

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 129–134 were read (grid search with purged CV, F1 scoring for meta-labeling, enhanced pipeline class, randomized search, log-uniform distribution, start of scoring discussion). Pages 135–137 (why `neg_log_loss` is preferred over accuracy for strategies, exercises) were **not** read.

**Fit with the platform:** the platform's sweeps are grid searches over strategy parameters. The chapter's two concrete ideas — **randomised search with a computational budget** and **log-uniform sampling** for scale parameters — transfer directly; the CV part applies once a learned component exists.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Hyper-parameter tuning is essential and a common source of overfitting; CV in finance must be purged and embargoed (ch. 7). | Overfitting by tuning. | 129 |
| C2 | **Grid search CV** exhaustively searches parameter combinations and scores them by CV; needs the purged k-fold generator, sample weights passed to the estimator, and optional bagging of the tuned estimator. | Baseline tuning. | 129–131 |
| C3 | **Scoring**: use **F1** when meta-labeling (a model that predicts "never act" gets high accuracy/log-loss but zero recall); accuracy or negative log-loss is fine when all classes matter; relabeling has no effect on accuracy/log-loss but affects F1. | Pick the right score. | 130 |
| C4 | **Randomised search CV**: for many parameters grids are intractable; sampling each parameter from a distribution (Bergstra et al.) (1) controls the **computational budget** regardless of dimensionality and (2) irrelevant parameters do not inflate search time as in a grid. | Budgeted search. | 131 |
| C5 | **Log-uniform distribution**: for non-negative parameters that respond multiplicatively (SVC `C`, `gamma`), sample values so that `log x` is uniform on `[log a, log b]`; uniform sampling on `[0, 100]` puts 99% of draws above 1 and wastes effort. | Scale-appropriate sampling. | 132–133 |
| C6 | Beginning of the argument for scoring investment strategies' hyper-parameters by negative log-loss rather than accuracy (rest not read). | Score choice. | 134 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Grid sweeps | ✅ | Sweeps with `MAX_SWEEP_RUNS`; user supplies the values. |
| Random search with budget and seed | ❌ | Grid only. |
| Log-spaced sampling | ❌ | No helper (also book 4 ch. 7 O1, ch. 17 O3, ch. 21 O2). |
| Purged/embargoed CV for tuning | ❌ | See ch. 7. |
| Appropriate scoring for filters | ❌ | Ranking by single metrics (net PnL etc.); no precision/recall of a filter. |

## 3. Opportunities

### O1 — Randomised sweeps with a budget, a seed and log-uniform integer/real distributions *(book: C4, C5, pp. 131–133)*
* **Proposal:** a sweep mode `random` with `n_trials`, `seed` and per-parameter distributions (`uniform`, `int_uniform`, `log_uniform`, `choice`), recorded in the sweep specification and result so runs are reproducible; combined with the **ledger/pre-declared ranges** (book 4 ch. 21 O2) and with the neighbourhood analysis (ch. 21 O1 needs a neighbour definition for irregular points: use distance in normalised log-parameter space). Log-uniform fits period parameters (EMA fast/slow, Donchian windows) and stop/ATR multiples.
* **Why:** budget independent of the number of parameters; irrelevant parameters (e.g. a filter threshold that does nothing) do not multiply the grid; consistent with the sampling advice of book 4 (geometric spacing, Monte Carlo sampling) with a published reference. 
* **Complexity:** low–medium (sampling plus storage plus neighbourhood in log-space). **Risks:** randomness can miss narrow optima (fine for robustness-seeking), results depend on the seed (store it), reproducibility of results requires the sampling code to be stable across versions. **Validation:** seeds reproduce the same points; log-uniform samples are uniform in log-space (KS test as in the book's snippet); `n_trials` honoured; integer rounding handles duplicates by counting distinct configurations.

### O2 — Score filters with F1/precision-recall in addition to P/L when tuning thresholds *(book: C3, p. 130)*
Link to ch. 3 O4: when a threshold (volatility filter, trend-strength filter) is tuned, a degenerate setting that "never acts" can look good on accuracy-style or even Sharpe measures in short samples; report F1, recall and number of trades alongside, and require a minimum trade count. **Complexity:** low.

### O3 — If ML tuning arises: purged k-fold + randomised search + bagged tuned estimator *(book: C1–C3)*
Part of the ML decision record (ch. 3 O3, ch. 6 O1, ch. 7 O4): no unpurged `GridSearchCV`; sample weights passed through; scoring defined per use (F1 for meta-labeling). **Complexity:** part of the ML track.

### Not applicable
sklearn pipeline bugs and workaround (until a library is chosen), SVC/RBF-specific parameters.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 randomised sweeps (log-uniform) | medium–high | – | – | low–medium | sweep spec, ledger |
| 2 | O2 filter scoring | medium | – | – | low | ch. 3 O4 |
| 3 | O3 ML tuning rules | – | – | – | ML track | approval |

## 5. Affected files
Sweep specification and service in `backtesting/application`, a sampling module in `backtesting/domain` (pure, seeded), `docs/openapi.json`, app sweep form (distribution choices), tests.

## 6. Incremental plan
1. Seeded samplers with unit tests; record specification.
2. Random sweep mode.
3. Neighbourhood analysis in log-space (with book 4 ch. 21 O1).

## 7. Acceptance criteria and tests
* Seeded sampling reproducible bit-for-bit; log-uniform passes a KS test on log-values; distinct configurations counted; sweeps without the new mode behave as today; ruff, mypy, tests green.

## Caveats
Randomised search has good properties for hyper-parameters in ML (Bergstra et al.), but for 2–3 trading-rule parameters a full grid with geometric spacing is feasible and easier to interpret; random search is mainly useful as the parameter count grows. The log-uniform distribution is described by the author as his own definition (it exists in scipy as `loguniform` today). Pages 134–137 were not read.
