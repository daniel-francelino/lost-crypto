# Book 2 · Chapter 7 — Intraday Momentum Strategies

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 155–168 was read. The MATLAB earnings-calendar scraper (Box 7.1) was read but is not summarised.

Examples are equity/futures/FX strategies with shorting, daily opens and closes, earnings calendars, ETF rebalancing and order books; results exclude costs and are 2004–2012. Most do not transfer to Lost Crypto.

## 1. Chapter summary (pp. 155–168)

| ID | Concept | Pages |
|---|---|---|
| C1 | Interday momentum has few independent signals (lower Sharpe, weak significance) and suffers after crises; **shorter intraday momentum avoids both**. All causes of momentum from Chapter 6 operate intraday except roll returns; a new one is the **triggering of stop orders** (breakouts). | 155–156 |
| C2 | **Opening gap strategy**: buy if the open exceeds the previous high by a fraction (0.1) of the 90-day daily-return standard deviation, sell short if below the previous low by the same; close at the day's end. FSTX futures: APR 13%, Sharpe 1.4 (2004–2012); GBPUSD with custom open/close times: APR 7.2%, Sharpe 1.3. Rationale: after a period without trading (overnight, weekend) stop orders trigger together and cascade. | 156–157 |
| C3 | **News-driven momentum**: post-earnings-announcement drift (enter at the open when the overnight return exceeds ½ standard deviation in either direction **without interpreting the news**, exit at the close): S&P 500, 2011–2012, APR 6.7%, Sharpe 1.5, only about 4× leverage possible; overnight holding had negative average returns, i.e. the drift horizon has shrunk to intraday. Other events (analyst changes, M&A about 3% APR, index composition changes) show similar shrinkage; macroeconomic releases showed no significant effect on EURUSD in the author's tests, and an older study found 10-minute GBPUSD momentum. | 157–163 |
| C4 | **Leveraged ETFs** must rebalance near the close in the direction of the day's move, creating momentum: buy DRN if the return to 15 minutes before the close exceeds +2%, short if below −2%: APR 15%, Sharpe 1.8 (Oct 2011–Oct 2012); effect grows with ETF assets. | 163–164 |
| C5 | **High-frequency**: bid/ask size imbalance predicts short-term price change (linear relation, stronger for low-volume stocks); tactics: joining the bid (ratio trade), ticking/quote matching, momentum ignition and flipping (deceptive order placement), stop hunting around support/resistance and round numbers, order flow (signed volume). The author notes that HFT profits come only from slower traders and that quote sizes have shrunk because of them. | 164–168 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Breakout momentum | ✅ | `donchian_breakout` is a close-above-N-bar-high breakout (the family of C2/C1), long-only. |
| Gap / session-open logic | n/a | Crypto trades 24/7; there is no overnight or weekend gap. A "daily open" (UTC 00:00) exists only by convention. |
| Intraday timeframes | ✅ | 1m, 5m, 15m, 1h, 4h, 1d candles are supported (`Timeframe`). |
| News/events, index changes, ETF rebalancing | ❌ / n/a | No event data. Exchange listing announcements and index rebalancing do not exist in the system. |
| Order book / order flow | ❌ | Only OHLCV candles are stored (`market_data/domain/models.py::Candle`: open, high, low, close, volume). No bid/ask, depth or signed volume. |
| High-frequency execution | n/a | REST-driven candle workflow with a 1-minute minimum; fills simulated at the next open. Not an HFT stack. |
| Costs at short horizons | ✅ | Fees and slippage always applied; the fill model uses fixed bps, which is optimistic at 1m. |

## 3. Opportunities

### O1 — Shorter-horizon trend research to raise independent signals *(book: C1, p. 155; ties to book 2 ch. 6 C7)*
* **Problem:** interday trend bots take few trades, so statistical confidence is weak (book 2 ch. 6). The book's remedy is shorter holding periods.
* **Proposal:** use the existing 5m/15m/1h timeframes in backtests and report, for each timeframe, number of independent round trips, cost drag and significance (book 2 ch. 1 O1), so the operator can see the trade-off. No new feature beyond the metrics already proposed; this is a research workflow note and a UI hint ("round trips needed").
* **Risk:** at short horizons costs and slippage dominate; the fixed-bps model is least realistic here (see O2).

### O2 — Size- and volatility-dependent slippage for short timeframes *(book: C5 and ch. 1 of this book; pp. 164–167 · adaptation)*
* **Problem:** a constant slippage understates cost on fast moves and thin books, which is exactly where intraday momentum operates, and the author warns that backtesting HF-like behaviour is unreliable (book 2 ch. 1 C7).
* **Proposal:** an optional slippage model scaled by recent volatility (for example candle range) and order size relative to candle volume; keep the fixed model as default; show a cost-sensitivity band (book 1 ch. 2 O4).
* **Benefit:** more honest short-timeframe backtests. **Complexity:** medium. **Risks:** a model with more parameters is another thing to fit; calibrate against recorded realised slippage (book 1 ch. 5 O4) instead of guessing. **Validation:** unit tests against hand-computed slippage; sensitivity of results.

### O3 — Candle-level order-flow proxy from taker volume *(book: C5, pp. 167–168 · adaptation, the book itself uses tick data)*
* **Problem:** only OHLCV is stored, but the book's order-flow idea (signed volume predicts short-term moves) needs buy/sell attribution.
* **Proposal (to verify before building):** exchange kline data typically carries taker-buy volume per candle (confirm for the Binance adapter and for the testnet); store it in an additive column and expose an "order-flow imbalance" feature (taker buy ÷ total volume) for diagnostics and, later, strategies. This is **our adaptation**; the book's evidence concerns tick-level order flow in stocks/futures/FX.
* **Benefit:** the only cheap path to microstructure-flavoured signals without a book feed. **Complexity:** medium (migration for stored candles, importer change, backfill). **Risks:** candle aggregation loses the within-candle timing the book relies on; extra stored data; no evidence of predictive power in crypto. **Validation:** import test with a fake source; correlation of the proxy with next-candle return on historical data as a pure diagnostic.

### O4 — Treat session-open ideas as inapplicable; do not port the gap strategy *(book: C2, pp. 156–157)*
No weekend/overnight gap exists in crypto spot. If a similar cascade mechanism is of interest, it would be a "break of the previous N-hour/N-day range", which the Donchian strategy already approximates. No work proposed.

### O5 — Event-driven momentum: backlog only *(book: C3, pp. 157–163)*
Needs machine-readable events (listings, delistings, protocol upgrades, macro releases). Record as **B-EVENTS**; no source exists today and the book reports that such effects have shrunk to intraday.

### Not applicable
Earnings drift, index changes, leveraged-ETF rebalancing, bid/ask imbalance, ticking, momentum ignition, flipping, stop hunting (the last two describe adversarial behaviour that the system should *defend against*, not copy; see below).

### Defensive note (our reading, not a book recommendation)
The book describes deceptive order tactics (momentum ignition, flipping, stop hunting). For a bot that uses market orders at known stop levels, the relevant lesson is that **visible stop levels and round-number clusters can be targeted**. The system already fills stops with a gap-through-open rule in simulation; no extra control is proposed, but realised-slippage tracking (book 1 ch. 5 O4) will show if stop fills are systematically worse than modelled.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O2 volatility/size-aware slippage | high | medium | – | medium | book 1 ch. 5 O4 (calibration data) |
| 2 | O1 timeframe trade-off view | medium | – | – | low | book 2 ch. 1 O1 |
| 3 | O3 taker-volume proxy | low (speculative) | – | – | medium | confirm exchange fields |
| 4 | O5 events | – | – | – | n/a | B-EVENTS |

## 5. Affected files
`execution/domain/fills.py` and `backtesting/domain/models.py` (slippage model option), `market_data/domain/models.py`, `orm.py`, importer and exchange adapters (O3, additive), app backtest form and detail, tests.

## 6. Incremental plan
1. Record realised slippage (book 1 ch. 5 O4) so the model can be calibrated.
2. Add an optional slippage model; keep the default unchanged.
3. Timeframe trade-off hints.
4. Check taker-volume availability; if present, store and run the diagnostic.

## 7. Acceptance criteria and tests
* The default backtest result is bit-for-bit unchanged when the new slippage option is off.
* New option has unit tests for volatility and size scaling and never produces favourable slippage.
* Any new candle column is nullable; existing candles and hashes (`hash_candles`) are unaffected unless the column is opted in.
* ruff, mypy and existing tests green.

## Caveats
The numbers (APR 7–15%, Sharpe 1.3–1.8) come from single-year or single-market samples, exclude costs, depend on instruments and microstructure that crypto spot does not share, and the author says that the duration of news-driven momentum keeps shrinking. Nothing in the chapter supports a claim about crypto profitability.
