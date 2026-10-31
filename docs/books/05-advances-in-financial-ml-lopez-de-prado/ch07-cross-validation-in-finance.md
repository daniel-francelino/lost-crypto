# Book 5 · Chapter 7 — Cross-Validation in Finance

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 103–111 were read (goal of CV, why k-fold fails, purging and embargo, the PurgedKFold class, sklearn bugs, exercise list). Snippets were skimmed.

**Relevance:** this is the validation chapter that any learned component (parameter selection by walk-forward, ML meta-labeling) must respect; the underlying concept — **leakage through overlapping information between train and test** — also applies to the platform's current train/test split and sweep selection.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | CV estimates generalisation error; testing on the training data is like lossy compression — "summarise the data with extreme fidelity, yet zero forecasting power". k-fold CV (partition into k subsets, train on k−1, test on the held-out) gives k metrics; for a binary classifier, learning is indicated if accuracy > 1/2. In finance CV is used for model development (e.g. hyper-parameters) and for backtesting. | Purpose of CV. | 103–104 |
| C2 | **Why k-fold fails in finance**: (1) observations are not IID (serial correlation, overlapping labels), so **leakage** puts information from the test set into the training set; with irrelevant features leakage creates **false discoveries**; (2) the test set is reused during development → **multiple testing and selection bias** (ch. 11–13). Leakage requires `(X_i, Y_i) ≈ (X_j, Y_j)`, not merely `X_i ≈ X_j` or `Y_i ≈ Y_j`. Mitigations: drop training observations whose labels depend on test information; avoid overfitting (early stopping, bagging with max_samples ≈ average uniqueness, sequential bootstrap). | Leakage. | 104–105 |
| C3 | **Purging**: remove from the training set any observation whose label interval overlaps the test labels' intervals (three overlap conditions on `[t_{j,0}, t_{j,1}]` and `[t_{i,0}, t_{i,1}]`). For a contiguous test set a single interval can be used. Diagnostic: if performance keeps improving as `k → T`, the backtest is profiting from leaks; after purging it should plateau. | Remove overlapping labels. | 105–107 |
| C4 | **Embargo**: besides purging, remove training observations that immediately **follow** a test set (serial correlation), by extending the test label end by `h`; `h ≈ 0.01 T` often suffices; no embargo is needed before the test set because training labels that end before the test begins contain only information available at test start. | Residual serial dependence. | 107–108 |
| C5 | **PurgedKFold** class: contiguous test folds (no shuffling), training set purged and embargoed using the label end times `t1`; "in general, we need to purge and embargo overlapping observations whenever we produce a train/test split, whether for hyper-parameter fitting, backtesting or performance evaluation". | Implementation. | 108–109 |
| C6 | **Bugs in scikit-learn CV**: scoring functions don't know `classes_`; `cross_val_score` doesn't pass sample weights to the log-loss scorer; use the book's `cvScore`. "You must always read all the code you run." | Tooling pitfalls. | 109–110 |
| C7 | Exercises: why shuffling before k-fold defeats CV in finance; compare shuffled k-fold, k-fold and purged k-fold on a dataset. | Practice. | 110–111 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Train/test split respects time order | ✅ | `backtesting/domain/segments.py`: one chronological split (no shuffling). |
| Purging of overlapping information at the split boundary | ❌ | Trades or indicator state open at the boundary can span both segments; indicators computed over the full series warm up on pre-test data (which is fine: past data) but a trade entered in train and exited in test contaminates both. Verify how `segments.py` treats positions across the cut. |
| Embargo | ❌ | None. |
| Multiple testing during selection on the test set | ❌ | Sweeps pick the best run on train/test and the user may iterate; no accounting (book 4 ch. 21 O2/O3). |
| k-fold or other CV | ❌ | None; parameters are not learned. |
| Leakage tests | ❌ | No truncation test (book 1 ch. 3 O2). |

## 3. Opportunities

### O1 — Boundary hygiene for the existing train/test split: purge trades crossing the cut and add an embargo *(book: C3, C4, pp. 105–108)*
* **Proposal:** (a) when evaluating the **test** segment, start with a flat position (no carry-over from the train segment) and ignore any trade whose entry is in the train segment; (b) when selecting parameters on the **train** segment, force-close (or discard) any position that would span the cut so that train results do not depend on test prices; (c) leave an **embargo gap** of `h` candles (default about 1% of the segment length, or the strategy's longest lookback/holding period, whichever is larger) between train and test so that serial correlation and indicator memory do not carry information across the boundary; (d) report whether the segments were purged/embargoed.
* **Why:** small but real leakage today possible via open trades and slow indicators at the boundary (EMA with long periods has memory of hundreds of candles; Donchian channels use windows). The book's diagnostic ("performance keeps improving when k grows") translates to checking whether results change when the embargo grows. **Complexity:** low–medium (segment logic and metric accounting). **Risks:** shortens usable test data; changes existing results (version the evaluation, keep the old behaviour behind a flag for reproducibility). **Validation:** a synthetic series with a planted look-ahead dependence across the cut is detected; with the embargo applied, the planted leak disappears; train results are invariant to test-segment prices (property test).

### O2 — Time-ordered cross-validation for sweeps instead of a single split ("purged blocked CV") *(book: C3–C5, pp. 105–109)*
Replace or complement the single split with **k contiguous test blocks**; for each block, select parameters on the remaining data with purging and embargo; report the distribution of out-of-sample results across blocks and the stability of selected parameters. This is walk-forward's non-sequential cousin (book 4 ch. 21 O4) and is the stepping stone to combinatorial purged CV (ch. 12). The caveats: for trend strategies on a drifting asset, a block in a bear market tests different regimes (that is useful); small k (5) is preferred because "excessive partitioning would again place in the testing set samples too similar to those used in the training set" (ch. 6). **Complexity:** medium–high (reuses the sweep engine; compute grows with k). **Validation:** no train observation overlaps any test interval plus embargo; deterministic; results for k = 1 equal the current split.

### O3 — Leakage test suite as part of CI *(book: C2, C3, pp. 104–107)*
Automated tests that (1) shuffle-vs-ordered comparison on a series with no signal (random walk): performance on a shuffled k-fold must be significantly better than on a purged k-fold for a dependent feature — demonstrating the leak — and (2) the truncation test for each strategy. These are regression guards for any future change in segmentation or feature code. **Complexity:** low–medium. **Validation:** by design.

### O4 — If an ML or learned component is introduced, use PurgedKFold with embargo as the only CV *(book: C5, C6, pp. 108–110)*
Same conclusion as chapter 6 O1: no shuffled k-fold, no OOB accuracy as the estimate; implement the purged k-fold with sample weights passed to the scorer; own scoring code (library bugs). **Complexity:** part of the ML track.

### Not applicable
The sklearn `KFold` subclass specifics and the bugs listed (until a library is chosen).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 leakage tests | high | – | high | low–medium | – |
| 2 | O1 boundary purge + embargo | high | – | – | low–medium | segments |
| 3 | O2 purged blocked CV | high | – | – | medium–high | O1 |
| 4 | O4 ML CV rules | high (future) | – | – | part of ML track | ML approval |

## 5. Affected files
`backtesting/domain/segments.py`, `backtesting/domain/engine.py` (flat start for test segment, forced close at the train cut), `backtesting/application/service.py` (embargo parameter, reporting), `docs/openapi.json`, app backtest form (segment options), tests.

## 6. Incremental plan
1. Leakage tests and the truncation test.
2. Boundary purge/embargo behind an option; record in the result.
3. Blocked purged CV for sweeps.

## 7. Acceptance criteria and tests
* A test dependent on boundary data fails before the change and passes after; default behaviour is unchanged unless the option is enabled; reproducibility hash includes the segmentation options; ruff, mypy, existing tests green.

## Caveats
The "h ≈ 0.01 T" embargo is a rule of thumb from the author's experience, not derived; k small vs large trade-offs are discussed qualitatively. The chapter proves nothing about generalisation of any specific strategy; it only controls one source of optimism (leakage) and acknowledges that multiple testing is a separate problem (chapters 11–14).
