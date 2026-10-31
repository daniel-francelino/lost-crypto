# Book 5 · Chapter 16 — Machine Learning Asset Allocation (Hierarchical Risk Parity)

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 221–227 were read in full (motivation, Markowitz's curse, hierarchical relationships, tree clustering). Stages 2–3 and the numerical example / Monte Carlo (pp. 228–245) were read only through headings and key sentences; appendices (proofs, code) and exercises were not read.

**Fit with the platform:** allocation across multiple assets/strategies. The platform trades one asset per bot with independent capital, so this is **future-facing** (same status as book 4 ch. 24). It is recorded because it is the book's answer to robust allocation and its warning against optimising on covariances applies to any allocator.

## 1. Chapter summary

| ID | Concept | Pages |
|---|---|---|
| C1 | **Hierarchical Risk Parity (HRP)** addresses three problems of quadratic optimisers (Markowitz CLA): **instability, concentration, underperformance**; it needs no inversion of the covariance matrix and works with singular/ill-conditioned matrices. Claim: Monte Carlo shows lower out-of-sample variance than CLA (even though CLA minimises variance) and than traditional risk parity. Applicable to allocating across multiple ML strategies. | 221 |
| C2 | **Markowitz's curse**: the more correlated the investments, the higher the condition number of the covariance matrix and the more unstable its inverse; estimation errors can offset diversification; at least `N(N+1)/2` IID observations are needed for a non-singular covariance (50 assets ≈ 5 years of daily IID data, an unrealistic stationarity assumption); even the naïve equal-weighted portfolio has beaten mean-variance and risk-based optimisation out-of-sample (De Miguel et al. 2009); CLA is very sensitive to small changes in expected returns (Michaud). | 222–223 |
| C3 | **Hierarchy instead of a complete graph**: a correlation matrix treats every investment as a substitute for every other (1,225 edges for 50 assets); a tree has `N − 1` edges, so weights rebalance only among peers and flow top-down. HRP stages: **(1) tree clustering** (distance `d_{i,j} = sqrt((1 − ρ_{i,j})/2)`, a proper metric; distance of distances; agglomerative linkage, e.g. nearest point; worked 3-asset example), **(2) quasi-diagonalisation** (reorder rows/columns so similar items are adjacent), **(3) recursive bisection** (split weights top-down by inverse-variance of cluster variances; inverse-variance allocation is optimal for a diagonal covariance). | 223–229 |
| C4 | **Numerical example** (10 assets, random data with some correlated columns): CLA concentrates 92.66% in the top-5 holdings and gives zero weight to 3 investments, HRP 62.57% in the top-5, inverse-variance (IVP) spreads ~10% each; in-sample std. dev. similar (HRP 0.4640 vs CLA slightly lower); **out-of-sample Monte Carlo** (with random shocks and jumps): portfolio variance CLA 0.1157, IVP 0.0928, **HRP 0.0671** — CLA's variance is 72.47% greater than HRP's. All mean returns ≈ 0. The author concludes HRP improves the out-of-sample Sharpe. (Simulation on synthetic data built by the author.) | 229–234 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Multi-asset allocation | ❌ | Independent bots; no allocator or portfolio module (book 4 ch. 24 diagnosis). |
| Correlation/covariance estimation | ❌ | — |
| Clustering of assets | ❌ | — |

## 3. Opportunities

### O1 — If a multi-bot allocator is ever built, start with **equal-risk (inverse-volatility) weights**, then consider HRP only with ≥ ~8–10 sufficiently different assets/strategies *(book: C2–C4)*
Given the book's own evidence (naïve and risk-parity portfolios are hard to beat out-of-sample; CLA is unstable), the simplest robust default is inverse-volatility allocation across bots (book 4 ch. 23/24); HRP is a second step if correlation structure matters. Crypto note (ours): with only a handful of liquid assets that are strongly correlated (one dominant factor), clustering adds little; strategies (trend vs mean reversion) may be the more meaningful leaves. **Complexity:** none now.

### O2 — HRP as a pure function for research (optional) *(book: C3, pp. 224–229)*
Implement correlation-distance, single-linkage clustering (scipy-free implementation possible), quasi-diagonalisation and recursive bisection on a covariance matrix; test with the book's 3-asset distance example (`D = [[0, .3873, .6325], [.3873, 0, .7746], [.6325, .7746, 0]]`, Euclidean distance of distances `[[0, .5659, .9747], [.5659, 0, 1.1225], [.9747, 1.1225, 0]]`, first cluster `(1, 2)`). Use inside the portfolio view (book 4 ch. 24 O1) as an *advisory* weight, never automatic. **Complexity:** medium. **Validation:** book examples; weights sum to 1; invariant to asset order; works on a singular covariance.

### O3 — Monte Carlo comparison of allocators on synthetic and bootstrapped data before adopting any *(book: C4, pp. 233–234 · ties to ch. 13 O1)*
Re-run the book's out-of-sample comparison (equal weight, IVP, HRP, minimum variance) on the platform's synthetic generator and on bootstrapped real returns of imported assets; adopt a method only if it wins consistently out-of-sample and survives costs/rebalancing. **Complexity:** medium. **Validation:** seeds reproducible.

### Not applicable
CLA internals and its Python implementation, the mathematical appendices (not read), large-universe applications.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 inverse-volatility default (decision record) | – | medium | – | doc | multi-bot portfolio view |
| 2 | O3 allocator comparison on synthetic data | medium | medium | – | medium | ch. 13 O1 |
| 3 | O2 HRP function | – | low | – | medium | — |

## 5. Affected files
Documentation; future `analytics/domain/portfolio` (HRP, IVP) and tests.

## 6. Incremental plan
Defer until the portfolio view and a second strategy family exist.

## 7. Acceptance criteria and tests
Book examples reproduce; weights nonnegative, sum to one, permutation-invariant; no automatic changes to bot capital.

## Caveats
All evidence in the pages read is simulation on data the author generated; the book claims historical confirmation by others (Kolanovic et al., Raffinot) without reproducing it here. The out-of-sample variance advantage concerns risk, not return, and ignores transaction costs of rebalancing. Pages 235–245 were not read in detail.
