# Book 5 · Chapter 6 — Ensemble Methods

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 93–102 were read in full (bias/variance/noise, bagging, random forest, boosting, bagging vs boosting in finance, bagging for scalability, exercises list). Code snippets were skimmed.

**Fit with the platform:** relevant only if an ML model is approved (ch. 3 O3). It supplies design rules for that model (bagging over boosting, how to avoid redundancy, why out-of-bag accuracy is misleading), not features for the current rule-based system. Nothing here should be built before the evaluation prerequisites (ch. 7, 12, 14).

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Three sources of error**: bias (unrealistic assumptions, underfitting), variance (sensitivity to small changes in the training set, overfitting; "mistaken noise with signal"), noise (irreducible). Mean-squared error = bias² + variance + noise. Ensembles of weak learners reduce bias and/or variance. | Diagnosing model error. | 93–94 |
| C2 | **Bagging**: fit `N` estimators on bootstrap samples (independent, parallelisable), average the forecasts or majority-vote. Variance of the bagged forecast `= σ̄²(ρ̄ + (1 − ρ̄)/N)`; bagging helps **only if the average correlation `ρ̄ < 1`** among estimators. A sufficiently large number of estimators makes majority voting more accurate than the individual ones **only if each is better than chance** (`p > 1/k`); bagging cannot rescue poor classifiers and reduces variance more than bias. | Variance reduction. | 94–97 |
| C3 | **Observation redundancy** (non-IID labels, ch. 4) has two detrimental effects: (1) bootstrap samples become near-identical, `ρ̄ ≈ 1`, so bagging does not reduce variance regardless of `N` (e.g. if labels span 100 bars, sample about 1% of observations per estimator); (2) **out-of-bag accuracy is inflated** because training and out-of-bag samples are almost identical; prefer a proper k-fold CV without shuffling (ch. 7) and a low k. | Misuse of bagging in finance. | 97–98 |
| C4 | **Random forest**: bagging plus random feature subsets per split (further decorrelation); provides feature importance (ch. 8) and out-of-bag accuracy (inflated in finance). With redundant samples it still overfits (nearly identical trees). Fixes: lower `max_features`; early stopping with `min_weight_fraction_leaf` (e.g. 5%) so OOB accuracy approaches out-of-sample CV accuracy; bag decision trees (or one-tree forests) with `max_samples = average uniqueness`; or replace the bootstrap with the sequential bootstrap; fit on a PCA of features; use `class_weight='balanced_subsample'`. | Controlling RF overfitting. | 98–99 |
| C5 | **Boosting** (AdaBoost): sequentially fit weak learners, up-weight misclassified observations, keep estimators better than chance; reduces both variance and bias. | Alternative ensemble. | 99–100 |
| C6 | **Bagging vs boosting in finance**: boosting addresses underfitting at the cost of greater overfitting risk; since financial data have low signal-to-noise ratio, "overfitting is often a greater concern than underfitting", so **bagging is generally preferable**; bagging is parallelisable. | Choice of ensemble. | 100–101 |
| C7 | **Bagging for scalability**: bag base learners that do not scale (SVM) with tight early stopping (`max_iter`, `tol`, `max_depth`); loss of individual quality is offset by variance reduction, yielding fast, robust estimates on huge datasets. | Compute. | 101 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| ML models, ensembles | ❌ | None in the code base. |
| Overfit control for any learned component | ⚠️ | Parameter search is a grid sweep with a train/test split; no correlation-aware or variance-aware treatment. |
| Parameter-ensemble ("bagging of rules") | ❌ | A single parameter set per bot. |

## 3. Opportunities

### O1 — If ML is added: choose bagging of shallow, early-stopped learners with `max_samples ≈ average uniqueness`; reject boosting by default *(book: C2–C6, pp. 94–101)*
Record these design constraints in the ML track decision record (ch. 3 O3): bagged decision trees with low depth, early stopping, `max_samples` tied to average uniqueness (ch. 4 O1), balanced class weights, probability outputs; measure `ρ̄` among tree predictions as a diagnostic (if `ρ̄ ≈ 1`, the ensemble adds nothing); never use OOB accuracy as the performance estimate; evaluate with purged CV (ch. 7) and at the system level (ch. 14). Boosting is allowed only as a documented experiment with out-of-sample proof. **Complexity:** none now (guidance); high when ML arrives.

### O2 — "Ensemble of rules" experiment: bag over parameter sets rather than learn a model *(book: C2, pp. 94–96 · our adaptation)*
The variance formula suggests an analogue for rule-based strategies: instead of picking one "best" parameter (selection bias), run an **ensemble of neighbouring parameter sets** (e.g. an EMA crossover for several fast/slow pairs on a log-spaced grid) and combine their signals by voting or averaging positions. If correlations among the members are below 1 the ensemble has lower variance of results than a single member; if the plateau is real (book 4 ch. 21) the ensemble reduces dependence on the exact choice. Evidence pipeline required; the platform currently has one parameter set per bot, so this would be a new "ensemble strategy" type. **H-PARAM-ENSEMBLE.** **Complexity:** medium. **Risks:** members are highly correlated (trend rules on the same prices), so benefits are small; execution is more complex (net position from votes); more trades if members disagree. **Validation:** compare with single best, with random member, and with the plateau centre on out-of-sample data; compute average member correlation.

### O3 — Condorcet / majority-vote check for combined signals *(book: C2, p. 96 · idea only)*
The accuracy gain from majority voting requires each voter to be better than chance and reasonably independent; before combining several signals (trend + breakout + mean reversion), measure each one's stand-alone hit rate and the correlation among them. Part of the portfolio/diversification view (book 4 ch. 24 O1/O5). **Complexity:** low.

### Not applicable
sklearn-specific bugs and class settings, SVM scalability, AdaBoost internals, PCA of features (until ML exists).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 design constraints (ML decision record) | high (future) | – | – | doc | – |
| 2 | O3 voting check | low | – | – | low | diagnostics |
| 3 | O2 parameter-ensemble experiment | medium | low | – | medium | sweep + pipeline |

## 5. Affected files
Documentation (`docs/books` decision record); for O2 `strategies/domain/` (ensemble strategy), registry, catalog; analytics for correlation of members.

## 6. Incremental plan
Keep O1 as guidance; evaluate O2 only after plateau analysis (book 4 ch. 21 O1) is available.

## 7. Acceptance criteria and tests
For O2: deterministic combined signal from member signals; correlation reported; defaults unaffected; truncation test for each member; ruff, mypy, tests green.

## Caveats
The bagging variance and accuracy formulas assume independent estimators for the accuracy result and an average pairwise correlation for the variance one; the book gives no empirical comparison of bagging vs boosting on financial data in these pages (the preference for bagging is an argument, not a measured result).
