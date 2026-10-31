# Book 5 · Chapter 18 — Entropy Features

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 263–267 (Shannon entropy, plug-in estimator, Lempel–Ziv/Kontoyiannis estimators start) and 275–276 (financial applications: market efficiency, maximum entropy generation, portfolio concentration start) were read. Pages 268–274 (encoding schemes, estimators' details, generalised mean/diversity) and 277–280 (exercises, references) were **not** read.

**Fit with the platform:** a *research feature* family. The book's claim that the information content (compressibility) of a price string indicates whether trend or mean-reversion bets pay off is a hypothesis, not a result in these pages.

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Price series reflect supply/demand with partial information; estimating the **informational content** of a series could give features: trend-following bets may be more profitable when prices carry *little* information and mean-reversion bets when prices carry *a lot* (the author's expectation). | 263 |
| C2 | **Shannon entropy** `H[X] = −Σ p[x] log₂ p[x]` (0 ≤ H ≤ log₂|A|), **redundancy** `R = 1 − H/log₂|A|`, **mutual information** `MI[X,Y] = H[X] + H[Y] − H[X,Y]` (for a bivariate normal, `MI = −½ log(1 − ρ²)`), and the normalised variation of information as a metric. | 263–264 |
| C3 | **Plug-in (maximum-likelihood) estimator** of the entropy rate on words of length `w` of a discretised sequence (e.g. return signs or quantile-encoded returns): `Ĥ_{n,w} = −(1/w) Σ p̂_w[y] log₂ p̂_w[y]`; needs `n ≫ w` for the empirical distribution to be close to the true one. | 264–265 |
| C4 | **Lempel–Ziv** compression-based complexity: more non-redundant substrings per message length means higher entropy; **Kontoyiannis** estimator uses the longest-match length `L_i^n` in a past window: `lim L_i^n / log₂ n = 1/H`, estimate `Ĥ = [ (1/k) Σ L_i^n / log₂ n ]⁻¹`; high-entropy messages give shorter matches. | 265–267 |
| C5 | **Applications**: **market efficiency** — a "decompressed" (high entropy, non-redundant) market is efficient; a "compressed" (low entropy) market is inefficient and bubbles form in compressed markets; **maximum entropy generation** (Fiedor) — the outcome maximising entropy is hardest for frequentist models to predict and may trigger stop-losses and runs; **portfolio concentration** — eigen-decomposition of the covariance matrix, factor loadings and the share of risk per principal component, to which an entropy-based concentration measure is applied (rest not read). | 275–276 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Entropy/compressibility features | ❌ | None. |
| Predictability diagnostics (autocorrelation, runs) | ❌ | Planned in book 4 ch. 15 O1 (sequence tables) and ch. 1 O1 (ER/noise). |

## 3. Opportunities

### O1 — Entropy and compressibility of candle-return sequences as a **diagnostic**, benchmarked against shuffled data *(book: C3, C4, pp. 264–267)*
* **Proposal:** discretise returns (sign, or quantile bins, e.g. 3 or 10 symbols) per asset/timeframe and compute the plug-in entropy rate for words of length `w = 1…~4`, and the Lempel–Ziv/Kontoyiannis complexity, in rolling windows; report each against the distribution obtained from **shuffled** copies of the same window (shuffling destroys sequential structure but keeps the marginal), giving a p-value-like "excess redundancy". Display rolling redundancy next to the efficiency-ratio and sequence diagnostics (book 4 ch. 1 O1, ch. 15 O1).
* **Why:** the same question as the sequence tables, with a different lens (information theory); shuffled baselines address the main weakness of raw entropy values, which depend on alphabet and window.
* **Complexity:** low–medium. **Risks:** estimation bias for short windows (`n` must greatly exceed `|A|^w`); thresholds are arbitrary; volatility clustering lowers entropy of absolute-return encodings without implying exploitable direction. **Validation:** i.i.d. random symbols give entropy near `log₂|A|` and zero excess redundancy; a periodic or Markov sequence is flagged; deterministic with a seed.

### O2 — Test the book's hypothesis (low entropy ↔ trend strategies work) with the existing strategies *(book: C1, C5, pp. 263, 275)*
Use O1 as a regime variable and ask whether `ema_crossover`/`donchian_breakout` trade outcomes (signal outcome table, ch. 3 O1; effective N, ch. 4 O1) differ between low- and high-entropy windows, across several assets, with the pipeline's multiple-testing accounting. **H-ENTROPY-REGIME.** **Complexity:** medium. **Risks:** one more regime variable among many (ER, volatility, SADF); high chance of spurious findings; treat as exploratory with a pre-declared hypothesis and a locked check.

### O3 — Portfolio concentration via principal-component risk shares (future portfolio view) *(book: C5, pp. 275–276)*
Compute eigenvalues of the correlation/covariance matrix of held assets and the share of risk per principal component; report an "effective number of independent bets" `exp(H)` of that distribution. A direct, interpretable replacement for naïve asset counts in the portfolio view (book 4 ch. 24 O1). **Complexity:** low–medium. **Validation:** identity covariance gives `N`; perfectly correlated assets give 1.

### Not applicable
Encoding schemes for quantile/sigma bars beyond a note (not read), maximum-entropy trading rules (speculative), microstructural entropy of order-flow signs (needs trade data).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 effective number of bets | – | medium | – | low–medium | portfolio view |
| 2 | O1 entropy diagnostic with shuffled baseline | low | – | – | low–medium | diagnostics module |
| 3 | O2 regime hypothesis test | medium | – | – | medium | O1, ch. 3/4 items |

## 5. Affected files
`analytics/domain/` (entropy estimators, shuffle baselines, principal-component shares), diagnostics page, tests.

## 6. Incremental plan
O3 with the portfolio view; O1 only if a regime-research track is opened; O2 last.

## 7. Acceptance criteria and tests
Estimators match closed forms on known distributions (fair coin → 1 bit, deterministic → 0); shuffled baselines reproduce the null; deterministic; ruff, mypy, existing tests green.

## Caveats
No empirical result linking entropy to strategy profitability appears in the pages read; the "compressed market ⇒ bubble" and "maximum entropy ⇒ black swan" ideas are conjectures from cited work. Pages 268–274 and 277–280 were not read.
