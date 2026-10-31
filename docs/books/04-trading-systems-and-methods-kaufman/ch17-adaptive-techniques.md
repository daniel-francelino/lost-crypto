# Book 4 · Chapter 17 — Adaptive Techniques

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 779–791 and 797–798 were read. The adaptive intraday breakout system (793–797) was only skimmed, and the pages on McGinley Dynamics detail, adaptive momentum variants and the closing "Considering Adaptive Methods" (790–796, 798–800) were read in part or not at all. The chapter's author is the book's author: KAMA is **his own method** (Smarter Trading, 1995), which is worth bearing in mind when reading the performance table.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | An **adaptive technique** changes with market conditions, mainly by automatically changing the calculation period of a trend or indicator: slow in sideways/noisy markets, fast in clean trends. The author concedes that **identifying a sideways market is very difficult** (a price can end where it started after a violent week). | One speed does not fit all conditions. | 779 |
| C2 | **KAMA (Kaufman's Adaptive Moving Average)**: `KAMA_t = KAMA_{t−1} + sc_t × (p_t − KAMA_{t−1})`, `sc_t = [ER_t × (fastest − slowest) + slowest]²`, `fastest = 2/(2+1)`, `slowest = 2/(30+1)` by default; `ER_t = |p_t − p_{t−n}| / Σ|p_i − p_{i−1}|` (the **efficiency ratio** of chapter 1; `n` ≈ 8–10, the length is capped by how many consecutive same-direction closes occur). Squaring makes the slow end an extremely slow trend (about 900 periods) and the fast end about a 4–5-period trend. Noise is not volatility (the drunken-sailor walk). **Practical rules**: `ER = 1` can occur with tiny drifts, so add a small filter for a minimum average change; because an exponential trendline flips direction whenever price crosses it, add a **small filter of trend-direction changes** (for example 0.1 standard deviations of the trendline changes); trade the **direction of the trendline**; keep `n` below 14; keep the upper bound at 30 (to desensitise, raise the lower bound above 2). | Noise-adjusted trend speed. | 779–783 |
| C3 | **Other adaptive averages**: Ehlers' **fractal adaptive MA** (fractal dimension), Chande's **VIDYA** (fixed constant 0.20 scaled by `k = stdev_n/stdev_m` of closes; the book notes returns might be better than prices), **correlation (r²) adaptive** average, Ehlers' **MAMA/FAMA** (phase rate of change; FAMA as signal line). | Variety of adaptation measures. | 783–786 |
| C4 | **Comparison, 1990–July 2011, 15 futures markets (Table 17.1), before costs**: average profit factor **KAMA 1.53**, MAMA 1.36, correlation 1.22, VIDYA 1.17; fewer trades per market goes with better results (KAMA ~159 trades, VIDYA ~443); all methods profitable on average; **S&P index results are weak** (KAMA 1.11, others < 1). A fair comparison to a fixed moving average is difficult because KAMA spans periods 5² to 30² (25–900): sample fixed periods with a progressive (log or exponential) distribution. | Evidence and its limits. | 786–788 |
| C5 | **Making momentum adaptive**: map any bounded oscillator to a 0–1 smoothing constant (`sc = M`, `|M|`, `M/100`, `|M/100|`); the adaptive RSI is more sensitive in sideways periods than KAMA unless squared; **adaptive stochastic** (look-back set from the efficiency ratio); **McGinley Dynamics** (`MD_t = MD_{t−1} + (p_t − MD_{t−1}) / (k·n·(p_t/MD_{t−1})^4)`, `k = 0.6`). | Extending the idea. | 788–790 |
| C6 | **An adaptive process**: re-test the system regularly on recent data (fixed length or after regime change); the problem is **not enough data**, "the faster you react, the less data there is to make a decision"; **development example**: a variable-length moving average whose period interpolates between 30 and 5 days according to where the price-change z-score sits between 0.25 and 1.75 standard deviations (Arrington). | Adapting by re-estimation or by volatility. | 797–798 |

Examples are futures. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Adaptive moving averages | ❌ | `ema_crossover` uses fixed-period EMAs. |
| Efficiency ratio | ❌ | Not computed anywhere (book 4 ch. 1 O1). |
| Trendline-direction filter against micro-flips | ❌ | Not applicable yet. |
| Fixed-period parameter grids sampled progressively | ❌ | See ch. 7 O1. |
| Periodic re-estimation of parameters | ❌ | B-WALK-FORWARD. |

## 3. Opportunities

### O1 — `kama_trend` strategy (experiment) *(book: C2, C4, pp. 779–788)*
* **Proposal:** a long-only trend strategy that holds when the KAMA trendline turns up and exits when it turns down, with parameters `er_period` (default 10), `fast_period` (2), `slow_period` (30) and `direction_filter` (minimum trendline change, in standard deviations of recent trendline changes). Sizing and risk go through the existing risk module. The implementation needs the efficiency ratio, the squared smoothing constant and a sample standard deviation, all expressible in `Decimal` with one documented float boundary for the standard deviation if needed.
* **Why:** KAMA is the one adaptive trend method with a direct noise-based rationale (book 4 ch. 1) and, in the author's own table, the highest profit factor and the fewest trades of the four; an adaptive trendline reduces whipsaw in noisy phases, which crypto has many of. **Caveats:** the author developed KAMA, so his comparison favours it; the results are before costs, in futures, and S&P index results were poor, i.e. in the noisiest market; whether it helps in crypto must be measured.
* **Complexity:** medium (new strategy file, registry, forms, tests). **Risks:** more parameters (5), correlation with other trend rules (effective N); the squared constant makes the slow end extremely slow (900-period equivalent), which can delay exits after reversals; edge cases when the trendline is flat. **Validation:** truncation test; ER boundary cases; comparison with a **progressively sampled** set of EMA periods (not one EMA), through the sweep → best-of-N → validation pipeline; cost sensitivity; stability across eras.

### O2 — Shared efficiency-ratio helper *(book: C2, p. 781)*
Used by the diagnostics (book 4 ch. 1 O1), the trend-quality filter (ch. 6 O1) and KAMA. Single implementation. **Complexity:** low.

### O3 — Fair comparison rule for adaptive vs fixed *(book: C4, p. 788)*
Add to the research guidelines: when comparing an adaptive method with a fixed-period one, sample the fixed periods log-spaced across the adaptive method's range and report the distribution of fixed results, not a single period. This avoids choosing an unlucky or lucky fixed benchmark. **Complexity:** documentation + sweep helper (ch. 7 O1).

### O4 — Adaptive process = periodic re-estimation: link to walk-forward *(book: C6, p. 797)*
The book's warning (little data when reacting fast) is the same trade-off as in the walk-forward design (book 3 ch. 6 O5). No separate work; the design of B-WALK-FORWARD must record how much data each re-estimation uses.

### O5 — Do not add VIDYA, r², MAMA/FAMA or McGinley without evidence *(book: C3, C5)*
They are alternative adaptation measures with the same purpose as KAMA; adding them multiplies the rule universe and the multiple-testing burden with near-duplicates. Prefer one adaptive method (KAMA) and compare it with fixed rules; add another only if a documented hypothesis says it behaves differently. **Complexity:** none.

### Not applicable
Fractal dimension and MESA/Hilbert phase methods (cycle-based, ch. 11 not pursued), adaptive intraday breakout optimisation, Arrington variable-length MA (superseded by KAMA for our purpose).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O2 ER helper | – | – | – | low | – |
| 2 | O3 comparison rule | high | – | – | doc | ch. 7 O1 |
| 3 | O1 KAMA strategy | medium | – | – | medium | O2; pipeline from book 3 |
| 4 | O5 no near-duplicates | – | – | – | none | – |
| 5 | O4 walk-forward link | – | – | – | – | B-WALK-FORWARD |

## 5. Affected files
`strategies/domain/` (helper and new strategy file), registry, `strategies/catalog.py`, app strategy forms and labels, tests including the truncation test, `check:consistency`.

## 6. Incremental plan
1. ER helper with the book's boundary cases.
2. KAMA strategy built behind the full validation pipeline (truncation test, cost sweep, best-of-N, validation lock).
3. Compare against the progressive sample of fixed EMA periods.

## 7. Acceptance criteria and tests
* ER = 1 for a straight line, ≈ 0 for an alternating series; KAMA with `ER ≡ 1` equals an EMA of period `fast` and with `ER ≡ 0` follows the squared slow constant; trendline flips are filtered by the threshold.
* No change to existing strategies; ruff, mypy and all tests green.

## Caveats
The performance table (average profit factors 1.17–1.53) is before costs, over unrelated futures markets including very trendy ones (Eurodollars), and was produced by the author of KAMA. The squared smoothing constants make KAMA far slower in noise than the nominal "30-period" suggests.
