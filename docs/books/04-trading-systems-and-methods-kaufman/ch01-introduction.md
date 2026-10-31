# Book 4 · Chapter 1 — Introduction

*Trading Systems and Methods*, 5th ed., Perry J. Kaufman (Wiley, 2013). Book pages (PDF page = book page + 20; the PDF text has some lost symbols). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. Pp. 1–24 were read, except p. 2–5 which were skimmed (overview of trading styles and fundamentals vs technical analysis) and pp. 16–17 (market maturity by region, reading list) which were only skimmed.

## 1. Chapter summary (pp. 1–24)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Random walk vs anticipation**: two arguments against pure randomness: decades of documented systematic performance, and prices moving on **anticipation**. Randomness depends on data frequency: the same series looks noisier at high frequency and trendier at long horizons; prices are **not symmetric nor normal**, with **fat tails in runs** (longer runs than a normal distribution implies). Reasons that methods work: flows unrelated to timing (monthly fund inflows/redemptions), anticipation, extreme volatility, price far from value. | Is trading possible at all. | 6–8 |
| C2 | **Style follows data frequency**: long-term trend followers should use low-frequency data (more trend visible); short-term traders favour mean reversion and fast moves with high-frequency data. | Match strategy and horizon. | 8–9 |
| C3 | **Measuring noise**: the **efficiency ratio (ER)** `= |P_t − P_{t−n}| / Σ|P_i − P_{i−1}|` (1 = straight line, 0 = pure noise), distinct from volatility; alternatives: **price density** (sum of highs minus lows over the n-day box height) and **fractal dimension** (estimated by a six-step procedure). The author prefers ER as the clearest. | Quantifying "how trendy". | 10–12 |
| C4 | **Evidence**: across futures and world equity indices (2000–Mar 2012), the average 20-day noise vs the profit factor of a basic always-in-market **40-day moving-average trend system without costs** shows a positive relation: **low noise → better trend following; high noise favours mean reversion**. Trendiest: short-term interest-rate futures, then longer rates, USD crosses, energy, metals; **equity indices were the noisiest and worst for trend following**. | Choosing the market and style by noise. | 13–14 |
| C5 | **Market maturity**: noise in North American equity indices rose over 20 years along with volume and participation; the same happens elsewhere. | Edge decay through participation. | 14–16 |
| C6 | **Eight research guidelines**: start from a sound premise (not discovered by testing everything); state it simply (Occam); assume nothing; try the simplest and most important parts first (transparent solutions); watch errors of omission (costs, risk); **question good results as hard as bad ones**; no shortcuts (verify others' work); start at the end (define the goal). | Research discipline. | 18–19 |
| C7 | **Profile of a trading system**: changing markets and system longevity (technology, participation, globalisation, falling costs); choice of data; diversification (can be across strategies in one market); **trade selection** (too many filters cause overfitting or no trades); **testing is for validation and robustness, not massive scanning** (a robust solution across many markets never looks as good as an optimised single-stock result); risk control at four levels (trade, sector, single-system portfolio, portfolio of systems; volatility-based risk management; leverage); **transaction costs** (fast systems most sensitive; directional systems have larger slippage than mean-reversion; **overstating costs is as harmful as understating**); **performance monitoring and feedback** against expectations. | Checklist for a complete system. | 20–23 |
| C8 | Occam's razor throughout: adding complexity for a few basis points increases problems and risk more than returns. | Simplicity as a principle. | 23 |

Examples are futures and equity indices. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Noise / efficiency ratio measurement | ❌ | Not computed anywhere; neither in `analytics/domain/metrics.py` nor in the market-data module. |
| Choosing timeframe by noise | ❌ | The operator picks one of six timeframes (`Timeframe`) without guidance. |
| Strategy family chosen by market character | ❌ | Only trend strategies exist. |
| Research guidelines | ⚠️ | Many are already in the product's constraints (simple strategies; costs always applied; train/test); others are missing (questioning good results, premise first). |
| Costs: both over- and under-stating are harmful | ⚠️ | Fixed fee and slippage; no calibration from realised execution (book 1 ch. 5 O4). |
| Directional vs mean-reversion slippage difference | ❌ | One slippage number for all strategies/sides. |
| Performance monitoring vs expectations | ⚠️ | Bot metrics and reconciliation exist; no comparison with backtest expectations (book 1 ch. 5). |

## 3. Opportunities

### O1 — Efficiency ratio (noise) diagnostics per pair and timeframe *(book: C3, C4, pp. 10–14)*
* **Problem:** the operator chooses a timeframe and a trend strategy without evidence that the series is trendy enough at that frequency.
* **Proposal:** add to the series diagnostics (book 2 ch. 2 O1, ch. 6 O1) the rolling `ER(n)` for a chosen window, its average and distribution (percentiles) by timeframe, shown for each imported pair, together with the *relationship the author measured*: lower noise → higher trend-system profit factor. Optionally compute the same relation on **our own data**: for each pair/timeframe, the basic always-in-market trend system's gross profit factor versus its average ER, replicating the book's scatter on the stored crypto candles. This tests the book's claim on crypto instead of assuming it.
* **Benefit:** a cheap pre-filter for strategy/timeframe choice, in the same family as the half-life and Hurst diagnostics, and a conditioning variable for results (performance by noise tercile). **Complexity:** low (pure function on closes, additive endpoint, chart rows in the app).
* **Risks:** the book's regression is on twelve years of futures and equity indices without costs; the relation may be weak or different in crypto; ER depends on the window; low ER at one timeframe can come from microstructure noise. **Validation:** synthetic straight-line series → ER = 1, alternating series → ER ≈ 0; reproduce the book's Table 1.1 numbers (0.06 and 0.56).

### O2 — Performance by noise regime *(book: C4, pp. 13–14 · adaptation)*
Split a backtest's results by ER tercile (computed on the same window) to show whether a trend strategy earns only in low-noise periods. Extends sub-period reporting (book 1 ch. 2 O5, book 2 ch. 5 O1). **Complexity:** low–medium. **Risk:** more slicing, more multiple-testing; label sample sizes.

### O3 — "Question the good results" checks as automated red flags *(book: C6, p. 19)*
Add to the run-screening block (book 2 ch. 1 O3): unusually high profit factor or Sharpe relative to the median of comparable runs; trade count too low; results far better than buy-and-hold with high drawdown mismatch; first/last trade dominating profit. The book is a guideline, not a threshold set. **Complexity:** low. **Validation:** unit tests per flag.

### O4 — Side- and strategy-aware slippage *(book: C7, p. 22 · adaptation)*
The author states directional (breakout/trend) systems suffer larger slippage than mean-reversion systems that provide liquidity. Make `slippage_bps` configurable **per entry type** (market entry on breakout vs limit-style entry) once a limit-order simulation exists; until then document that the single-bps model likely understates trend-entry cost and overstates a limit-order strategy's. Ties to book 2 ch. 7 O2. **Complexity:** medium. **Depends on:** realised-slippage records (book 1 ch. 5 O4).

### O5 — Feedback loop checklist in the runbook *(book: C7, pp. 22–23)*
Document: expected metrics at go-live, a comparison cadence and the decision rule for changing size or retiring (ties to book 2 ch. 4 O1, book 2 ch. 8 O7). **Complexity:** very low.

### Not applicable
Futures-specific market lists, regional equity noise rankings, reading list, spreadsheet/EasyLanguage notation.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 ER diagnostics | medium | – | – | low | diagnostics module |
| 2 | O3 good-results flags | medium | – | – | low | metrics |
| 3 | O2 performance by noise | medium | – | – | low–medium | O1 |
| 4 | O5 runbook | – | medium | – | very low | – |
| 5 | O4 slippage by type | medium | – | – | medium | execution records |

## 5. Affected files
`analytics/domain/` (ER, price density), `market_data/presentation/router.py` (diagnostics), `backtesting/domain/segments.py` or a new regime splitter, app market-data page (`lib/market-data/*`), `docs/` runbook, tests.

## 6. Incremental plan
1. Pure ER function with the book's example as a test.
2. Endpoint and app chart.
3. Own-data replication of the noise-vs-trend-profit relation (research report).
4. Red flags and regime splits.

## 7. Acceptance criteria and tests
* ER reproduces Table 1.1 (0.06 and 0.56) and the boundary cases (1.0 and ≈ 0).
* Diagnostics are read-only and do not change trading or stored runs; ruff, mypy, existing tests green.

## Caveats
The noise–profit relation uses a cost-free, always-in-market trend system on futures and equity indices (p. 13). It is the author's evidence for his framework, not a rule for crypto spot, and past relations may not persist.
