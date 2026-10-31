# Book 5 · Chapter 4 — Sample Weights

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 59–70 were read (overlapping outcomes, concurrent labels, average uniqueness, bagging and sequential bootstrap incl. the Monte Carlo experiment, return attribution weights, start of time decay). The rest of time decay and "class weights" (pp. 70–73) and exercises were not read.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Overlapping outcomes**: with labels spanning `[t_{i,0}, t_{i,1}]` (e.g. triple-barrier), two labels depend on the same returns whenever `t_{i,1} > t_{i+1,0}`, so labels are **not IID**. Restricting the horizon to avoid overlap is "a terrible solution". Analogy: blood spilt from each tube into the nine next ones. Most ML theory assumes IID. | Dependence between labels. | 59–60 |
| C2 | **Concurrency**: `c_t = Σ_i 1_{t,i}` is the number of labels that depend on the return `r_{t−1,t}`; **uniqueness** of label `i` at `t` is `u_{t,i} = 1_{t,i}/c_t`; **average uniqueness** `ū_i` = mean of `u_{t,i}` over its lifespan = reciprocal of the harmonic average of `c_t`; it uses future information (`t_{i,1}`) but only on the training set with labels, not as a predictive feature, "hence no information leakage". | Quantify overlap. | 60–62 |
| C3 | **Bagging and uniqueness**: bootstrap draws about `1 − 1/e ≈ 2/3` unique items of `I`; if the maximum number of non-overlapping outcomes is `K << I`, the unique fraction expected is `1 − e^(−K/I)`, so assuming IID leads to **oversampling**: in-bag observations are redundant and similar to the out-of-bag ones, so (1) a random forest becomes copies of one overfit tree and (2) **out-of-bag accuracy is grossly inflated**. Remedies: don't drop overlapping observations (loses too much); set `max_samples` ≈ average uniqueness; or **sequential bootstrap**. | Why standard bagging fails. | 62–63 |
| C4 | **Sequential bootstrap**: draw observations one by one with probability proportional to the average uniqueness each candidate would have if added to the already drawn set; redundancy is penalised but not forbidden; numerical example with three labels (`p = {5/14, 3/14, 6/14}` for the second draw). **Monte Carlo experiment** (random `t1`): median average uniqueness 0.6 for the standard bootstrap vs 0.7 for the sequential one (ANOVA p ≈ 0). | Samples closer to IID. | 63–68 |
| C5 | **Return attribution weights**: `w̃_i = |Σ_{t=t_{i,0}}^{t_{i,1}} r_{t−1,t}/c_t|`, rescaled so `Σ w_i = I`; weight depends on both uniqueness and the absolute return attributable to the label; not appropriate with "neutral" labels — "I would generally advise you to drop neutral cases". | Weighting for training. | 68–69 |
| C6 | **Time decay**: markets are adaptive systems (Lo), so older observations should weigh less; decay factor `d[x] ∈ [0, 1]` multiplies the sample weights by cumulative uniqueness; (detail beyond the first lines not read). | Non-stationarity. | 70 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Overlap-aware evaluation | ❌ | The backtester evaluates trades individually without any adjustment; trades from one strategy are sequential and non-overlapping (one position at a time), so the P/L series itself has no overlapping outcomes. Overlap would appear in **signal-level outcomes** (ch. 3 O1) and in multi-bot/multi-asset analysis. |
| Concurrent labels / uniqueness | ❌ | None. |
| Bagging, forests | ❌ | No ML. |
| Sample weighting, time decay | ❌ | None. |
| Effective sample size reporting | ❌ | Reports count trades; for overlapping signal outcomes the effective count is smaller. |

## 3. Opportunities

### O1 — Effective sample size for signal-level statistics *(book: C1, C2, pp. 59–62)*
For the signal outcome table proposed in ch. 3 O1, compute **concurrency** `c_t` and **average uniqueness** per signal, and report **effective N = Σ ū_i** (or N × mean uniqueness) next to every statistic (win rate, mean return, hit-rate of barriers) so that confidence intervals use the effective, not nominal, count. For example, 300 daily-timeframe signals with 20-day outcomes overlap heavily; effective evidence may be a fraction. Also useful for the bot's own consecutive trades if exits are delayed and entries occur before earlier exits (not possible with one position at a time, but possible across bots on the same asset). **Complexity:** low. **Risks:** the uniqueness is defined on the label's lifespan only; it is a first-order correction, not a full dependence model. **Validation:** the book's numerical example (labels over `[0,3]`, `[2,4]`, `[4,6]`) reproduces `p = {5/14, 3/14, 6/14}` for the second draw and the indicator matrix; non-overlapping labels give `ū = 1`.

### O2 — Use average uniqueness when calling a signal-level result "significant" *(book: C3, p. 62–63; links to book 3)*
In the evidence pipeline (book 3, book 4 ch. 21), t-tests, bootstrap and permutation tests on signal outcomes must be run on independent units: block-bootstrap or tests on effective N. The book's finding that out-of-bag/in-bag similarity inflates accuracy is the same dependence problem seen from the validation side (chapter 7). **Complexity:** low–medium (a rule plus the effective N from O1). **Validation:** on synthetic overlapping outcomes with no edge, the false-positive rate of the test at 5% stays near 5% when effective N is used and exceeds it when nominal N is used.

### O3 — Sequential bootstrap and uniqueness weights (only if ML is introduced) *(book: C4, C5, pp. 63–69)*
Implement indicator matrix, average uniqueness, sequential bootstrap and return-attribution weights as pure functions with the book's numerical example as a unit test. Do not build them until a model that needs them (meta-labeling, ch. 3 O3) is approved. Note the cost: the sequential bootstrap is `O(I²)` in naive form and the book needed multiprocessing for its Monte Carlo (6 hours on 24 cores for 10⁶ iterations of 10 observations) — prefer sampling subsets or the `max_samples ≈ ū` shortcut. **Complexity:** medium; defer.

### O4 — Time-decay as an option in rolling re-estimation / walk-forward *(book: C6, p. 70)*
When walk-forward or periodic re-estimation of parameters exists (book 4 ch. 21 O4), allow an optional recency weighting (older windows count less) and report the sensitivity. The book argues markets adapt; the cost is fewer effective data points, which is already scarce in crypto. Part of the walk-forward design; **complexity:** low once available.

### Not applicable
Random forest bagging internals, `BaggingClassifier` settings, multiprocessing engine details (ch. 20), class-weight balancing (not read).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 effective N for signal outcomes | high | – | – | low | ch. 3 O1 |
| 2 | O2 significance on effective N | high | – | – | low–medium | O1 |
| 3 | O4 time decay option | low | – | – | low | walk-forward |
| 4 | O3 sequential bootstrap + weights | medium (with ML) | – | – | medium | ML track approval |

## 5. Affected files
`analytics/domain/` (concurrency, uniqueness, effective N, optional bootstrap), tests with the book's numerical example; app views showing effective N.

## 6. Incremental plan
1. Concurrency/uniqueness functions with the numerical example as a test.
2. Show effective N beside every signal-level statistic.
3. Use it in significance tests.
4. Sequential bootstrap only with ML.

## 7. Acceptance criteria and tests
* Indicator matrix and average uniqueness equal the values derived by hand for the three-label example; non-overlapping labels yield 1; effective N ≤ nominal N.
* Sequential bootstrap (if built) has higher mean uniqueness than the standard bootstrap on random `t1` with fixed seeds; deterministic given a seed.
* ruff, mypy and existing tests green.

## Caveats
The Monte Carlo evidence is a simulation on synthetic overlaps (median uniqueness 0.6 vs 0.7), not on market data. Weighting by absolute return attributes more importance to large moves, which may focus the model on rare crypto crashes; it is a design choice, not a result. Time decay details were not read.
