# Book 5 · Chapter 2 — Financial Data Structures

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 23–41 were read (data types, standard and information-driven bars, multi-product series incl. the ETF trick, PCA weights and futures roll, sampling features and the CUSUM filter, exercises list). The code snippets were skimmed; formulas for imbalance and runs bars were read at the level of definition.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Do not consume someone else's processed dataset; start from raw data to find informative features. Four data types: **fundamental** (released with a lag; align to the release date, not the period end; backfilled/reinstated values introduce look-ahead; "a substantial number of findings in papers cannot be reproduced once data is aligned correctly"), **market**, **analytics** (derived, costly, opaque), **alternative**. | Data alignment and look-ahead. | 23–25 |
| C2 | **Time bars should be avoided**: markets do not process information at a constant time interval (the hour after the open is more active than noon), so time bars oversample low-activity periods and undersample high-activity ones; time-sampled series show serial correlation, heteroscedasticity and non-normality. | Sampling choice. | 25–26 |
| C3 | **Tick bars** (sample every N transactions; Mandelbrot–Taylor: returns over a fixed number of transactions are closer to Gaussian), **volume bars** (every N units; avoids order-fragmentation arbitrariness; Clark 1973: closer to IID Normal), **dollar bars** (every N units of currency exchanged; robust to price changes and to corporate actions; the number of dollar bars per day is more stable over the years than tick or volume bars for a fixed bar size — Figure 2.1; bar size may be adapted dynamically). Beware auction trades that look like one tick. | Activity-based sampling. | 26–28 |
| C4 | **Information-driven bars**: tick, volume and dollar **imbalance bars** (sample when the cumulative signed tick/volume/dollar imbalance exceeds its expectation; signs from the **tick rule** `b_t = b_{t−1}` if `Δp = 0`, else `sign(Δp)`; expectations by exponentially weighted averages of previous bars) and **runs bars** (sample when the longest run of one side exceeds its expectation). Idea: sample more often when informed traders arrive. | Sampling by order-flow information. | 29–32 |
| C5 | **Multi-product series**: events that alter the series (rolls, dividends, rebalancing, spread weights) create structural breaks. **ETF trick**: build a series of the value of $1 invested in a basket/spread (positive, includes carry and costs) so code can treat any basket as a single cash product; rebalance costs, bid-ask and volume (limited by the least active member) are tracked separately. **PCA weights** for hedge ratios; **single-future roll**: subtract the cumulative roll gaps from prices; rolled prices can become negative, so form a non-negative series from returns computed on raw prior prices. | Continuous series for futures/spreads. | 32–37 |
| C6 | **Sampling features**: downsampling for reduction (linspace or uniform) vs **event-based sampling**: place bets after an event (structural break, extracted signal, microstructure phenomenon) and let the model learn whether the event is actionable. **Symmetric CUSUM filter**: `S⁺_t = max(0, S⁺_{t−1} + y_t − E_{t−1}[y_t])`, `S⁻_t = min(0, S⁻_{t−1} + y_t − E_{t−1}[y_t])`; sample a bar when `S⁺ > h` or `S⁻ < −h`, then reset; with `E_{t−1}[y_t] = y_{t−1}` for first differences. Unlike Bollinger-band crossing it **does not fire repeatedly while the series hovers around a threshold** — "it requires a full run of length h". | Choosing which observations to model. | 38–40 |
| C7 | Exercises compare tick/volume/dollar bars on serial correlation, stability of weekly bar counts, variance of variances and Jarque–Bera statistics (results are asked of the reader, not given). | Empirical comparison method. | 40–41 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Time bars | ✅ (only) | `Candle` is time-sampled (timeframes 1m–1d); the whole stack assumes fixed timeframes. |
| Volume/dollar bars | ❌ | `Candle` carries volume (base volume and probably quote volume — verify in `market_data/domain/models.py`) but only fixed-interval klines are imported. Binance klines include quote asset volume and number of trades, so **tick/volume/dollar bars can be approximated from candles only roughly**; precise bars need aggregated trades (`aggTrades`) with the `isBuyerMaker` flag, which the platform does not import. |
| Tick-rule / order-flow imbalance | ❌ | No trade-level data. |
| Look-ahead / alignment | ✅ (candles) | Candle close time is known; fills happen at the next open. Fundamental/alt data not used. |
| Rolls / continuous futures | n/a | Spot only. |
| Event-based sampling (CUSUM) | ❌ | Strategies evaluate every candle; no event sampler. |
| Candle gaps/integrity (data structure quality) | ❌ | See book 4 ch. 22 O1. |

## 3. Opportunities

### O1 — Dollar-volume diagnostics on existing candles, before any new bar type *(book: C2, C3, pp. 25–28)*
* **Proposal:** in the series diagnostics, compute per timeframe: (a) the **distribution of quote volume per candle** and its coefficient of variation across hours of the day and days of the week, (b) the **serial correlation of returns** and of absolute returns, (c) the **normality** of returns (kurtosis, Jarque–Bera) for the time-sampled candles, and (d) the same statistics for **approximate dollar bars** built by aggregating 1-minute candles until a dollar threshold is reached (if 1m candles are imported). This answers, with the platform's own data, whether the book's claim (activity-based sampling has better statistical properties) holds for the pair being traded.
* **Why:** it is cheap, read-only and decides whether the expensive trade-level work (O2) is worth it. **Complexity:** low–medium. **Risks:** aggregating 1m candles to dollar bars is an approximation (a candle spans a range of prices); bars may exceed the threshold within one candle. Mark as diagnostic only. **Validation:** a synthetic series with known heteroscedasticity should show improvement under dollar sampling; time-based results unchanged.

### O2 — Dollar bars (and optionally imbalance bars) from trade data as a research data product *(book: C3, C4, pp. 27–32)*
Import Binance aggregate trades for selected pairs, store them compactly (Parquet or partitioned tables; volumes are large), and build **dollar bars** with a threshold chosen so that the average bars/day equals the current timeframe's count. Optionally add **dollar imbalance bars** with the tick rule (Binance provides `isBuyerMaker`, so the aggressor side is known — better than the tick rule). Strategies would remain candle-based unless they explicitly opt in; the backtester would need a candle-like object (OHLCV + start/end time) per bar, which already fits the `Candle` model if the "timeframe" becomes "bar type + threshold".
* **Costs/risks:** large storage and import time (aggTrades for BTCUSDT is hundreds of millions of rows over years), rate limits, data quality, and a larger engine change: timestamps are no longer on a fixed grid, so indicators defined on "per day" or annualisation need per-bar timing; fees/slippage models by time are affected. **Recommend only after O1 shows benefits** and after the evidence pipeline is in place. **Complexity:** high.

### O3 — CUSUM event filter as a research tool (events for labeling and for gating signals) *(book: C6, pp. 38–40)*
Implement the symmetric CUSUM filter in the analytics domain (pure function: series of log prices or returns + threshold → event timestamps). Uses: (a) sampling bars for labeling/model training in chapter 3 onward; (b) a **signal gate** for existing strategies: only act when a CUSUM event confirms a move of size `h` (reduces repeated signals while price hovers); (c) display events on the chart. The threshold `h` can be a multiple of rolling volatility (the book uses a fixed h but notes variants). **Complexity:** low. **Risks:** an extra parameter; interacts with the trend rules; treat the gated variant as a hypothesis through the pipeline (**H-CUSUM-GATE**). **Validation:** monotone random walk fires at fixed spacing; a series hovering around a level does not retrigger (the book's contrast with Bollinger bands); truncation test.

### O4 — Data alignment rules as a written invariant for any new feed *(book: C1, pp. 23–24)*
If funding rates, open interest, on-chain or sentiment data are ever added, each datum must be keyed by the time it became **publicly available**, never by the period it describes; store the release timestamp and any revisions (vintage). Crypto examples (ours): funding rate is published at set times; on-chain metrics are aggregated daily by providers that may restate; sentiment indices have publication lags. Add the rule to the project's data guidelines now so it is not forgotten. **Complexity:** documentation. **Validation (future):** tests that features at time t never use values with release time > t.

### Not applicable
Fundamental and analyst data, satellite and other alternative data, futures rolls and the ETF trick (spot only), PCA weights for spreads, auction-trade handling in equities. The ETF trick may become relevant if cross-asset spreads or pairs trading (book 1/2) are added; not now.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O4 data alignment invariant (docs) | high (future) | – | – | doc | – |
| 2 | O1 dollar-volume diagnostics | medium | – | – | low–medium | diagnostics module |
| 3 | O3 CUSUM filter | medium | – | – | low | – |
| 4 | O2 dollar/imbalance bars from trades | medium–high | – | – | high | O1 result |

## 5. Affected files
`analytics/domain/` (diagnostics, CUSUM), `market_data` (trade import and storage, only for O2), `backtesting/domain` (bar abstraction, only for O2), app diagnostics page, docs/data guidelines, tests.

## 6. Incremental plan
1. Data alignment rule written; CUSUM function with tests.
2. Diagnostics comparing candle statistics (and 1m-aggregated dollar bars if available).
3. Decide on trade-level import after reading the results.

## 7. Acceptance criteria and tests
* CUSUM: fires exactly when the cumulative drift crosses ±h and resets; no repeated fires at a flat level; deterministic.
* Diagnostics produce the same numbers on fixtures computed by hand; read-only; ruff, mypy and existing tests green.

## Caveats
The statistical-superiority claims for tick/volume/dollar bars come from cited papers (Mandelbrot–Taylor, Clark, Easley et al.) and mostly equity/futures data; the book gives its own figure but no table with crypto results. The imbalance and runs bars rely on trade data and on exponentially weighted expectations whose parameters (initial expected bar size, lookback) are arbitrary and can make bar counts unstable; the book acknowledges parameters but does not provide a robustness study in these pages.
