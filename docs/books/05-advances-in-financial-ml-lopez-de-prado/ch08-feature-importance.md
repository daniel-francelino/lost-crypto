# Book 5 · Chapter 8 — Feature Importance

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 113–121 and the start of 121 (parallelised vs stacked importance) were read. Pages 122–127 (stacked importance, the synthetic-data experiments with informative/redundant/noise features and their results, exercises) were **not** read.

**Fit with the platform:** the chapter's headline — "backtesting is not a research tool; feature importance is" — is a research-process principle that applies to the platform even without ML (what drives a strategy's results?). The techniques (MDI, MDA, SFI, PCA orthogonalisation) apply once a model exists.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **The backtest-and-repeat cycle is the most pervasive mistake**: running data through an algorithm, backtesting, and repeating until a good-looking backtest appears "will likely lead to a false discovery"; statisticians consider it scientific fraud (ASA guidelines); **"it typically takes about 20 such iterations to discover a (false) investment strategy at the standard 5% significance level"**. | Research-by-backtest. | 113 |
| C2 | **Importance of feature importance**: before any backtest, fit a classifier on `(X, y)`, evaluate with **purged k-fold CV** (ch. 7), then ask which features carry the performance; then study when they matter (regimes), whether they matter for other instruments and asset classes, and which features are consistent across the universe. **"Backtesting is not a research tool. Feature importance is."** | Research methodology. | 113–114 |
| C3 | **Substitution effects** (multicollinearity) dilute or hide the importance of related features. **MDI (mean decrease impurity)**: fast, in-sample, tree-specific; sums to 1; masking effects (use random feature subsets and treat zeros as NaN); biased toward some predictors; two identical features each get half. **MDA (mean decrease accuracy)**: slow, out-of-sample, any classifier; permute one feature column at a time and measure the loss in OOS score (accuracy, negative log-loss or F1); with two identical features MDA marks **both** as unimportant; can conclude that **all** features are unimportant; requires purged and embargoed CV. | Methods with substitution effects. | 114–117 |
| C4 | **SFI (single feature importance)**: OOS score of each feature alone; no substitution effects; can also conclude that all features are unimportant; loses joint and hierarchical effects. **Orthogonal features** by PCA on standardised features (keep components explaining ≥95% variance) as a partial cure for linear substitution; PCA ranks features without labels, so **agreement between the PCA ranking and the label-based importance (weighted Kendall's tau; example 0.82) is evidence the pattern is not entirely overfit**. | Methods without substitution effects and a sanity check. | 117–121 |
| C5 | **Parallelised vs stacked**: compute importance per instrument and aggregate across the universe; features important across many instruments and criteria are more likely to reflect a real phenomenon (fast, parallel; substitution effects may still hide important features in a single instrument). | Universe-wide research. | 121 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Feature-importance analysis | ❌ | No features/model. |
| Research-by-backtest guard (iteration count) | ❌ | Users can rerun backtests and sweeps without limit; nothing counts or discounts iterations (book 4 ch. 21 O2). |
| Attribution of results to rule components | ❌ | No ablation tool (book 4 ch. 8 O7). |
| Cross-asset consistency view | ❌ | See book 4 ch. 21 O10. |
| Regime dependence of a strategy | ❌ | No conditional performance by volatility/trend regime. |

## 3. Opportunities

### O1 — Make the iteration count visible: "N backtests/sweeps run on this data" with the 20-iterations warning *(book: C1, p. 113)*
Show, for each (asset, timeframe, date range) dataset and strategy family, the cumulative number of backtests and sweep members executed, with a plain-language note: with a 5% significance level and ~20 independent tries, a false "discovery" is expected (the book's claim; the arithmetic is `1 − 0.95^20 ≈ 64%`, and the exact figure of 20 corresponds to the expected count of 1 false positive at 5%). Feeds the deflated Sharpe ratio (ch. 14). Same as book 4 ch. 21 O2 and this book ch. 1 O3. **Complexity:** low. **Validation:** counters match the number of stored runs.

### O2 — Component attribution instead of "optimise the whole": ablation/permutation analysis for rule-based strategies *(book: C2, C3, pp. 113–117 · our adaptation)*
The rule-based analogue of MDA/SFI: (a) **ablation**: run the strategy with each component removed or neutralised (a filter off, stop off, exit rule replaced by a time exit) and report the change in outcome-based metrics; (b) **permutation test of inputs**: for features/filters derived from a series (e.g. volatility, volume), shuffle the feature across time (preserving its distribution) and measure the loss of performance — if shuffling changes nothing, the component contributes nothing; (c) report on the **signal outcome table** (book 5 ch. 3 O1) so that attribution is independent of path-dependent exits. Together this realises "use feature importance, not backtests, to research". **Complexity:** medium. **Risks:** interactions (a component that works only with another, the SFI limitation); limited sample. **Validation:** a planted component with known effect is recovered; a noise component shows no effect.

### O3 — Cross-asset / cross-regime consistency of component importance *(book: C2, C5, pp. 114, 121 · links to book 4 ch. 21 O10)*
Repeat O2 across assets (BTC, ETH, SOL, …) and across regime slices (high vs low volatility, bull vs bear, defined without labels) and report which components are consistently important; consistent ones deserve study of the mechanism (book 5 ch. 1 O3). **Complexity:** medium. **Caveats:** crypto assets are strongly correlated; regimes defined in-sample can be overfit.

### O4 — If an ML model is built: use MDI + MDA + SFI with purged CV and PCA agreement check *(book: C3, C4, pp. 114–121)*
Decision-record guidance for the ML track (ch. 3 O3): compute all three importance types, expect substitution effects between correlated technical features (many indicators are monotone transformations of each other), orthogonalise before MDI/MDA, report the weighted Kendall's tau between importance and PCA rank, and accept that "all features unimportant" is a valid outcome (do not proceed to a backtest). **Complexity:** part of the ML track.

### Not applicable
Code details for sklearn `RandomForest`/`BaggingClassifier`, stacked importance computations (not read), the synthetic-data experiments (not read).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 iteration counter + warning | high | – | – | low | run storage |
| 2 | O2 component attribution (ablation/permutation) | high | – | – | medium | ch. 3 O1; book 4 ch. 8 O7 |
| 3 | O3 cross-asset/regime consistency | medium | – | – | medium | O2 |
| 4 | O4 ML importance guidance | – | – | – | part of ML track | ML approval |

## 5. Affected files
Run-storage queries and an analytics endpoint for counts; `analytics/domain/` (ablation and permutation harness); app research page; docs.

## 6. Incremental plan
1. Counters and warning text.
2. Ablation harness over the signal outcome table.
3. Cross-asset/regime views.

## 7. Acceptance criteria and tests
* Counters equal stored run counts; ablation recovers a planted effect and shows ≈0 for noise on synthetic data; permutation preserves the marginal distribution of the shuffled feature; deterministic with a seed; ruff, mypy and existing tests green.

## Caveats
"About 20 iterations" is a back-of-the-envelope illustration (expected false positives at 5%), not an empirical measurement. The claim that "backtesting is not a research tool" is a position of the author: the book later builds backtest methodology (ch. 10–16), i.e. it means backtests should come after, not instead of, analysis of what drives predictions. Pages 122–127 were not read.
