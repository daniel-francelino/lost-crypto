# Book 5 · Chapter 19 — Microstructural Features

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 281–286 were read (motivation, literature review, tick rule, Roll model, high-low volatility, Corwin–Schultz). The second generation (Kyle's, Amihud's, Hasbrouck's lambda, pp. 286–290), third generation (PIN/VPIN, pp. 290–293) and additional features (pp. 293–296) were seen by headings and first sentences only, and are **not** summarised in detail.

**Fit with the platform:** the platform has candles (OHLCV), no trades, no order book. Only features computable from OHLCV are practical: the **Corwin–Schultz spread**, **Parkinson/Beckers high-low volatility** and (from the headings) an **Amihud-type illiquidity** ratio. Order-flow features (tick rule, VPIN, Kyle/Hasbrouck lambda, cancellation rates) need trade or book data.

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Microstructure data (FIX messages: cancellations, queues, partial fills, aggressor side) are among the most important ingredients for predictive ML features. Three generations: (1) price-sequence models (tick rule, Roll 1984), (2) volume/strategic-trade models (Kyle 1985, Amihud 2002), (3) sequential-trade models (PIN, Easley et al. 1996; VPIN under volume sampling) where the bid-ask spread is the premium market makers charge for being adversely selected. | 281–282 |
| C2 | **Tick rule**: aggressor side `b_t = sign(Δp_t)`, or `b_{t−1}` if the price is unchanged; high accuracy despite simplicity; transformations of `{b_t}` give features (Kalman-filtered expectation, structural breaks, entropy, t-values of cumulative sums, fractional differentiation). | 282 |
| C3 | **Roll model**: observed price = mid-price ± half-spread `c` with random aggressor side; implies `c = sqrt(max{0, −cov[Δp_t, Δp_{t−1}]})` and `σ²_u = σ²[Δp] + 2 cov[Δp_t, Δp_{t−1}]`; useful for thinly quoted instruments; assumptions (no drift, homoscedastic, serially independent signs) are contradicted empirically but plausible under proper sampling (ch. 2). | 282–283 |
| C4 | **High-low volatility** (Parkinson 1980; Beckers 1983): `E[(1/T) Σ log²(H_t/L_t)] = k₁σ²_{HL}`, `k₁ = 4 log 2`; `E[(1/T) Σ log(H_t/L_t)] = k₂σ_{HL}`, `k₂ = sqrt(8/π)`; more accurate than close-to-close volatility. | 283–284 |
| C5 | **Corwin–Schultz (2012) bid-ask spread estimator from high and low prices**: highs are mostly matched against the offer and lows against the bid; the volatility component of the high/low ratio grows proportionally with the time elapsed, the spread component does not; with `β_t = E[Σ_{j=0..1} log²(H_{t−j}/L_{t−j})]` (single-bar ranges over 2 bars), `γ_t = log²(H_{t−1,t}/L_{t−1,t})` (range over 2 bars), `α_t = (√(2β_t) − √β_t)/(3 − 2√2) − √(γ_t/(3 − 2√2))`, the spread is `S_t = 2(e^{α_t} − 1)/(1 + e^{α_t})`; set negative alphas to 0 (as the authors recommend); a rolling estimate over sample length `sl` can be smoothed with a Kalman filter; the volatility estimate is a by-product. | 284–286 |
| C6 | Second generation focuses on **illiquidity** (a priced risk) via regressions on signed volume (Kyle's, Amihud's and Hasbrouck's lambda); third generation on informed-trading probability (PIN, VPIN) — headings only. | 286–293 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| OHLCV candles incl. volume | ✅ | `Candle` (volume unused by strategies). |
| Trades / aggressor side / order book | ❌ | Not imported (Binance offers aggTrades with `isBuyerMaker`, and depth snapshots/streams). |
| Spread estimate from candles | ❌ | Fixed `slippage_bps`. |
| Illiquidity measures | ❌ | None. |

## 3. Opportunities

### O1 — High-low volatility (Parkinson) and Corwin–Schultz spread as candle-based diagnostics *(book: C4, C5, pp. 283–286)*
* **Proposal:** implement both estimators over candles; rolling spread (sample length 20–100), report mean spread in bps per asset/timeframe and its time-of-day profile; compare with the platform's assumed `slippage_bps` (a data-driven sanity check on the cost model: the estimate approximates the effective half-/full spread, not market impact for a given order size); Parkinson volatility becomes a second volatility option next to ATR and close-to-close (book 4 ch. 20 O1).
* **Why:** a zero-new-data way to ground costs in data and to detect illiquid periods; for liquid Binance spot pairs the estimated spread will be tiny and probably dominated by the exchange's quoted spread (1–2 bps for majors), so the main use is for less liquid pairs and for stress periods. **Complexity:** low. **Risks:** the estimator assumes continuous trading and Brownian prices; 1-minute candles on thin pairs yield noisy/zero estimates (negative alphas truncated); it estimates spread, not slippage from size. **Validation:** closed-form checks on simulated prices with a known spread and volatility (Corwin–Schultz's own simulation approach); non-negativity; formulas re-checked against the paper before shipping (extraction garbled the constants).

### O2 — Amihud-type illiquidity ratio `|r| / quote volume` per candle/day *(book: C6 heading; formula not read — definition from the original paper)*
Rolling average of absolute return divided by dollar volume as a coarse illiquidity feature (price impact per dollar). Use as a filter or a risk input (pause when illiquidity spikes), after validating on data. Must read p. 288 before implementing to follow the book's exact definition. **Complexity:** low. **H-ILLIQ-FILTER** only through the pipeline.

### O3 — Trade-level data (aggressor side, order flow imbalance, VPIN) — recorded, deferred *(book: C1, C2, C6; ch. 2 O2)*
Needs trade or depth data and storage; many features (tick rule, signed volume imbalance, serial correlation of order flow, VPIN) depend on it. Binance aggTrades expose the aggressor flag so the tick rule is unnecessary. Decide together with the dollar-bar work (ch. 2 O2). The book itself says microstructural features are the "most important ingredients"; the evidence in the pages read is theoretical and from the author's experience. **Complexity:** high.

### O4 — Use spread/illiquidity estimates to set the slippage model by timeframe and time of day *(book: C5; links to book 4 ch. 16 O2, ch. 20 O5)*
Replace a constant `slippage_bps` by a table indexed by pair and hour, calibrated from O1 and, later, from the platform's own recorded fills. **Complexity:** medium.

### Not applicable
Bond-market BWIC applications, options markets, TWAP footprints, cancellation rates (no order data), PIN/VPIN estimation details.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 Parkinson volatility + Corwin–Schultz | medium | medium | – | low | candles |
| 2 | O4 spread-informed slippage table | high | medium | – | medium | O1; fills records |
| 3 | O2 Amihud ratio | low | low | – | low | read p. 288 |
| 4 | O3 trade-level data | medium–high | – | – | high | decision |

## 5. Affected files
`analytics/domain/` (estimators), diagnostics page, `execution/domain/fills.py` (cost table, later), tests.

## 6. Incremental plan
Estimators + diagnostics; calibrate the cost model; postpone trade-level data.

## 7. Acceptance criteria and tests
Estimators recover known spreads/volatilities in simulations; truncation/causality respected; deterministic; ruff, mypy, tests green.

## Caveats
The Corwin–Schultz constants and algebra above were reconstructed from a partly garbled extraction and must be verified against the paper. Both estimators are low-frequency proxies. The chapter provides no evidence of predictive value of these features for returns. Pages 286–296 were skimmed only.
