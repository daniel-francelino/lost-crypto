# Book 5 · Chapter 14 — Backtest Statistics

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 195–207 and the start of attribution (p. 207) were read. Pages 208–210 (rest of attribution, exercises, references) were not read. Several formulas were garbled by text extraction (notably PSR/DSR); they are restated here from the visible fragments and from the standard published definitions (Bailey & López de Prado 2012, 2014) — the form below is **checked against the visible structure of the formulas on pp. 203–204** but should be re-verified against the book before implementation.

**Relevance:** this is the central statistics chapter for the platform's metrics and evidence pipeline: the Probabilistic Sharpe Ratio, the Deflated Sharpe Ratio, bets vs trades, concentration of returns, drawdown/time under water, implementation-shortfall metrics and the "Third Law of Backtesting".

## 1. Chapter summary

| ID | Concept | Pages |
|---|---|---|
| C1 | Seven families of backtest statistics: general characteristics, performance, runs/drawdowns, implementation shortfall, return/risk efficiency, classification scores, attribution. Report what investors use to compare; metrics should uncover asymmetric risk or low capacity. | 195 |
| C2 | **General characteristics**: time range (the test should include enough regimes), average AUM, capacity (a minimum AUM for sizing/diversification; performance decays as AUM grows), leverage (with costs), **maximum dollar position size** (prefer strategies whose maximum position is close to average AUM, i.e. not relying on extreme events), ratio of longs (long-short ideally ≈ 0.5), **frequency of bets**: a **bet** = a sequence of positions on the same side (ends when flattened or flipped), so the number of bets is ≤ number of trades; "a trade count would overestimate the number of independent opportunities"; **average holding period** (weighted), **annualised turnover** (dollar traded per year ÷ average AUM; can be high with few bets if the position is constantly tuned), **correlation to the underlying universe** (significant correlation means the strategy is merely holding or shorting the universe). | 196–197 |
| C3 | **Performance**: PnL, PnL from longs, annualised rate of return, hit ratio, average return from hits and from misses; **time-weighted rate of return (TWRR)** per GIPS, geometrically linked, adjusted for external cash flows. | 198–199 |
| C4 | **Runs**: returns are rarely IID; runs (uninterrupted same-sign sequences) increase downside risk. **Returns concentration** via a Herfindahl-Hirschman–style index: `h⁺ = (Σ (w_t⁺)² − 1/n)/(1 − 1/n)` on positive-bet weights (0 = uniform, 1 = one return holds everything), same for negative returns `h⁻` and for bets per month; **drawdown (DD)** = loss between consecutive high-water marks and **time under water (TuW)** = time from a high-water mark until the PnL exceeds it; runs statistics: HHI of positive returns, of negative returns, of bets per month; 95th-percentile drawdown and time under water. | 199–202 |
| C5 | **Implementation shortfall**: brokerage fees per turnover, **slippage per turnover**, dollar performance per turnover, return on execution costs (performance ÷ total costs — "should be a large multiple" so the strategy survives worse-than-expected execution; also the cost multiple at which the strategy breaks even). | 202–203 |
| C6 | **Sharpe ratio** `SR = μ/σ` (IID Gaussian excess returns); estimation error is substantial. **Probabilistic Sharpe Ratio**: `PSR[SR*] = Z[ (SR̂ − SR*)·sqrt(T−1) / sqrt(1 − γ̂₃·SR̂ + ((γ̂₄ − 1)/4)·SR̂²) ]`, where `T` = number of returns, `γ̂₃` skewness, `γ̂₄` kurtosis (3 for Gaussian), `SR̂` the observed non-annualised Sharpe; PSR rises with SR̂, with longer track records and positive skew and falls with fat tails. **Deflated Sharpe Ratio**: `DSR = PSR[SR*]` where the benchmark `SR*` is the expected maximum Sharpe among `N` independent trials under the null: `SR* = sqrt(V[{SR̂_n}])·((1−γ)·Z⁻¹[1 − 1/N] + γ·Z⁻¹[1 − 1/(N e)])`, γ ≈ 0.5772 (Euler–Mascheroni), `V[{SR̂_n}]` the variance of the estimated Sharpe ratios across trials. The expected maximum is positive even if the true SR is zero and grows quickly with `N` and with the variance of trials. **Marcos' Third Law of Backtesting:** "Every backtest result must be reported in conjunction with all the trials involved in its production. Absent that information, it is impossible to assess the backtest's false-discovery probability." | 203–205 |
| C7 | **Efficiency statistics**: annualised Sharpe `SR·sqrt(a)` (a = observations per year; assumes IID), information ratio (excess return over benchmark ÷ tracking error), PSR, DSR (should exceed 0.95 for 5% significance). | 205–206 |
| C8 | **Classification scores** for the meta-labeling overlay: accuracy, precision, recall, F1 (harmonic mean), negative log-loss; Table 14.1 lists the four degenerate cases (observed all 1s, all 0s, predicted all 1s, all 0s) where precision/recall/F1 are undefined or equal to others — scikit-learn sets F1 to 0 with a warning. | 206–207 |
| C9 | **Attribution**: decompose PnL by risk class (duration, credit, liquidity, sector, currency…); risks are not orthogonal (rest not read). | 207 |

## 2. Diagnosis (verified in code)

| Metric | Status | Evidence / notes |
|---|---|---|
| Net PnL, return, buy&hold, max drawdown, fees, win rate, profit factor, avg trade | ✅ | `analytics/domain/metrics.py`. |
| Sharpe/Sortino/Calmar, annualisation | ❌ | Not present (book 4 ch. 23 O1 plans these). |
| PSR, DSR | ❌ | — |
| Skewness/kurtosis of returns | ❌ | — |
| Number of bets vs trades | ≈ | One position at a time, long-only: trades ≈ bets (each round trip = one bet). |
| Average holding period, turnover | ⚠️ | Holding time can be derived from trades (verify it is reported); turnover not reported. |
| Time under water, drawdown percentiles | ❌ | Only max drawdown. |
| Concentration (HHI) of returns | ❌ | — |
| Correlation with the underlying | ❌ | Buy&hold return reported, not correlation. |
| Implementation shortfall metrics | ⚠️ | Total fees and slippage are accounted; ratios (performance ÷ costs, break-even cost multiple) not reported. |
| Classification scores | ❌ | No classifiers. |
| Attribution | ❌ | — |
| Trial count for deflation | ❌ | See ch. 11 O1. |

## 3. Opportunities

### O1 — Add PSR and DSR to the sweep/backtest results *(book: C6, C7, pp. 203–206)*
* **Proposal:** compute per-period (e.g. daily) returns from the equity curve, then: observed non-annualised Sharpe `SR̂`, skewness, kurtosis, `T`, **PSR against a benchmark Sharpe (default 0)**, and, for sweeps and for any backtest with a ledger count `N` (ch. 11 O1), the **DSR** using `N` = the number of independent trials and `V` = the empirical variance of the trials' Sharpe ratios. Display "Probability the strategy's Sharpe is truly > 0: PSR 0.82; after deflation for 200 trials: DSR 0.31" with an explanation, thresholds (≥ 0.95) and warnings (small T, fat tails, non-IID).
* **Why:** it converts "best of N" into a probability, the one statistic that directly counters the sweep's selection bias; needs only returns and the trial count. Together with PBO (ch. 11) it forms the minimal "credibility" panel.
* **Subtleties to handle:** (a) choose the return frequency consistently (daily returns for 1h-bar strategies give fewer observations; the formula uses non-annualised SR at the sampling frequency); (b) "independent trials": parameter neighbours are highly correlated, so the effective number of independent trials is smaller than the count of runs (the book gives no estimator in the pages read; options: cluster trials by return correlation, use the number of distinct strategy families × parameter plateaus, or report DSR under several N and show sensitivity); (c) autocorrelation of returns violates IID: report a Newey–West or block-adjusted variance as a sensitivity; (d) equity curve of a position that is flat for long stretches has many zero returns, which lowers measured σ and inflates SR (book 4 ch. 24, same issue as the allocation) — also report SR computed on **bet returns** and on active periods.
* **Complexity:** low–medium (formulas, inverse normal CDF, ledger integration). **Validation:** compare against reference implementations on fixtures (white noise → PSR ≈ 0.5 at SR* = 0; DSR decreases with N; as N → 1 DSR → PSR); symmetric properties.

### O2 — Extended statistics bundle (general, runs, shortfall) *(book: C2, C4, C5, pp. 196–203)*
Add to the metrics layer: **bets vs trades** (explicit definitions), **average holding period**, **annualised turnover**, **time in market**, **correlation to the underlying's returns**, **HHI concentration of positive/negative returns and of monthly returns**, **drawdown series, time under water, 95th-percentile drawdown and TuW**, and implementation-shortfall ratios (**performance ÷ total costs**, **break-even cost multiple**, **slippage per turnover**). Overlaps with book 4 ch. 21 O7 and ch. 23 O1: define each metric once with its book reference. **Complexity:** low–medium. **Validation:** closed-form fixtures; HHI bounds 0–1 (uniform = 0, single return = 1); TuW consistent with the equity curve; metrics invariant to constant scaling of equity.

### O3 — Report results together with the trials (Third Law) as a product rule *(book: C6, p. 205)*
Every displayed performance number for a configuration chosen from a search must be shown with: number of trials (raw and effective), date range of data, the family of strategies tried, and whether the evaluation segment was locked. Absent that information the UI marks the result "unverified: selection bias unknown". **Complexity:** low–medium (depends on the ledger). **Validation:** results without a ledger entry show the warning.

### O4 — Capacity and size sanity for a spot account *(book: C2, p. 196)*
Report approximate **capacity** hints: average and maximum position notional vs average daily quote volume of the pair (participation rate), and warn when the configured capital would exceed a small share (e.g. 1% of per-candle volume, ch. 20 O5 of book 4). For retail sizes capacity is rarely binding but the check documents that. **Complexity:** low.

### O5 — Classification scores for filters (and for any future meta-model), including degenerate-case handling *(book: C8, pp. 206–207)*
Implement accuracy/precision/recall/F1/log-loss and the degenerate cases explicitly (return None/NaN with explanation, not 0) in the filter evaluation (ch. 3 O4). **Complexity:** low. **Validation:** Table 14.1 cases.

### O6 — Time-weighted return handling for deposits/withdrawals (only if capital flows are ever modelled) *(book: C3, pp. 198–199)*
Bots have fixed capital; no external flows. If withdrawals or top-ups are introduced, use TWRR (geometric linking of sub-period returns) rather than simple PnL ratios. **Complexity:** none now.

### Not applicable
GIPS compliance reporting, bond-specific dirty price/accrued interest terms in TWRR, long-short ratios, attribution by risk classes (single-asset long-only).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 PSR and DSR | very high | – | – | low–medium | ledger (ch. 11 O1) for DSR |
| 2 | O2 extended statistics | high | high | – | low–medium | equity series |
| 3 | O3 results with trials | very high | – | – | low–medium | ledger |
| 4 | O5 classification scores | medium | – | – | low | ch. 3 O1/O4 |
| 5 | O4 capacity hint | low | low | – | low | volume data |
| 6 | O6 TWRR | – | – | – | – | not needed |

## 5. Affected files
`analytics/domain/metrics.py` (new statistics: returns series, SR, skew, kurtosis, PSR, DSR, HHI, TuW), a normal CDF/inverse CDF helper (use `statistics.NormalDist` from the standard library if precision suffices), backtest result schema and `docs/openapi.json`, app result pages, tests with reference values.

## 6. Incremental plan
1. Returns series and basic statistics (SR, skew, kurtosis) with unit tests.
2. PSR; then DSR with the ledger count and sensitivity table.
3. Extended statistics (runs, shortfall, turnover).
4. UI "credibility panel" combining PSR, DSR, PBO, and the Third Law notice.

## 7. Acceptance criteria and tests
* PSR: for `SR̂ = 0`, `SR* = 0` returns 0.5; monotone increasing in `SR̂` and `T`; decreasing in kurtosis; DSR ≤ PSR(0) for `N > 1` and decreasing in `N`; matches published example values (to be verified against the original papers before shipping).
* Statistics are deterministic, scale-invariant where appropriate and documented with formulas and references.
* ruff, mypy, existing tests green.

## Caveats
PSR/DSR assume IID returns with the estimated skew/kurtosis, independent trials, and a null of zero skill; crypto returns are heteroscedastic and autocorrelated at some horizons, and parameter trials are strongly dependent, so DSR with N = number of runs is conservative while DSR with N = 1 is optimistic. The book's DSR needs the variance of trial Sharpes, which must be computed on the same return frequency. The formulas should be validated against the primary papers (Bailey & López de Prado 2012, 2014) before implementation because the PDF extraction of this chapter is imperfect. Pages 208–210 (rest of attribution, exercises) were not read.
