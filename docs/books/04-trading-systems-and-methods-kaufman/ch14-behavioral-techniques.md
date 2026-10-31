# Book 4 · Chapter 14 — Behavioral Techniques

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 617–620 (news), 623–628 (**event trading**) and 648–649 (Fibonacci) were read. The rest — news scoring continuation (620–622), the Commitment of Traders report, opinion and contrary opinion (635–647), Elliott waves, Fibonacci price targets, Fischer's compass, Gann and financial astrology (649–684) — was **not** read in detail. Elliott, Fibonacci, Gann and astrology are subjective or non-testable methods that the project excludes (see [book 3 ch. 1](../03-evidence-based-technical-analysis-aronson/ch01-objective-rules-and-their-evaluation.md)).

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Short-term systems target **investor behaviour** more than macro factors. News is "the greatest single element affecting pricing"; quantifying it (scoring items +/−, e.g. scheduled reports) is hard; a study scoring Wall Street Journal items found the news favoured the current market direction about 70% of the time around turning points, concluding that the market mostly reflects the news. Markets react to anticipation, and to reports from any major economy during stress. | News as input. | 617–619 |
| C2 | **Media coverage is a lagging, consensus indicator** (headlines about a drought or a bull market appear at the extremes). | Contrary signals. | 623 |
| C3 | **Event trading**: two situations — scheduled reports (modest moves, usually faded) and **price shocks** from unexpected news (largest volatility, "out of proportion with normal trading risk"; many traders never plan for them). The profit is not in positioning ahead of the report (50% chance, high risk) but in **studying the pattern after the initial reaction**. After a shock there is continuation (underreaction/structural change) or reversal (overreaction) over the next ~3 days; the relationship between the size of the reaction and the later pattern must be measured (small shock → continuation, very large → possible overreaction). Candidate events need enough volatility, a favourable likelihood and/or a hedging role. | Trading the aftermath, not the event. | 623–625 |
| C4 | **Expectations are in the price just before a report**; surprise = actual versus expected. **Measuring an event**: `volatility ratio = true range_t / average true range over the previous n days, lagged m days`, typically `n = 60`, `m = 30`; **ratio > 3.0 flags a likely news shock**; use true range because shocks can open as gaps. | Detecting shocks objectively. | 625–626 |
| C5 | **Rules (Warwick)**: buy at the close if the market closes in the **upper 20% of the day's range** on an event day and history shows continuation; hold a predetermined number of days based on the lag pattern; use a stop. An old corn study: 81% of the change on the event day, a typical 8% reversal over four days, and a net 27% in the original direction over 45 days. Typical sequence: price shocks hit interest rates first, then currencies, then equities, with unstable lags. | Concrete rule and its limits. | 627–628 |
| C6 | **Fibonacci** series and ratios have become part of price analysis; the book presents coincidences ("interesting to some, significant to others"); statements are not testable as given. | Context only. | 648–649 |

Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Shock detection (volatility ratio) | ❌ | Only the suspect-candle filter (`max_candle_range_pct`, default 25%) in `risk_management/domain/models.py`, which blocks entries on very large ranges, a crude shock guard; no ratio against recent volatility. |
| Post-shock behaviour studied | ❌ | None. |
| Plan for price shocks | ⚠️ | Native exchange stops, kill switch, daily-loss/drawdown pauses, global exposure caps; no analysis of how the strategies behave across historical crypto shocks. |
| News/events | ❌ | None (B-EVENTS). |
| Subjective methods | n/a | Excluded. |

## 3. Opportunities

### O1 — Volatility-ratio shock detector and post-shock study (research tool) *(book: C3, C4, C5, pp. 624–627)*
* **Proposal:** the book's `volatility ratio` (true range today divided by the lagged average true range; defaults 60/30; threshold 3.0) as a pure function; a diagnostics report over a pair/timeframe that finds shock candles and reports, for horizons of 1–5 candles, the forward return **conditioned on the direction of the shock and on where the close sits in the range (upper/lower 20%)**, with sample sizes, eras and the unconditional benchmark. This replicates the book's event study using only candles, with no news feed (shock = abnormal candle regardless of cause).
* **Benefit:** tells the operator whether crypto shocks tend to continue or revert at the timeframe they trade, informs stop/size rules and whether a "pause after a shock" or "trade the aftermath" idea has any basis. **Complexity:** low–medium.
* **Risks:** the pages describe event days for scheduled reports; crypto shocks have mixed causes (liquidations, hacks, listings); small sample; multiple testing across horizons, thresholds and close-location classes. **Validation:** synthetic series with injected shocks followed by planted continuation/reversal.

### O2 — Shock-aware risk behaviour (pause or reduce after a shock) *(book: C3, C4, pp. 623, 626)*
* **Proposal:** an optional risk limit: after a candle with volatility ratio above a threshold, block new entries for `k` candles (an extension of `max_candle_range_pct`, which only looks at the current candle), or reduce size. The book states that price shocks are the main survival risk and that most traders do not plan for them; this is a cheap guard consistent with the existing risk module. Default off; evaluate through O1 and the backtester's risk-aware mode (book 1 ch. 5 O2).
* **Risks:** may block the best entries (breakouts often happen on shocks); unknown net effect. **Complexity:** low. **Validation:** unit tests; backtest comparison with and without the guard.

### O3 — Stress scenarios: replay historical shocks against live-risk settings *(book: C3, p. 623; links to ch. 21–22)*
Build a small library of historical crypto shock windows from the stored candles (found by O1) and run each bot configuration through them as a stress test (loss and slippage under the worst candles), reporting the worst single-candle and 3-candle drawdowns versus the configured caps. **Complexity:** medium. Cross-reference to price-shock testing in Kaufman ch. 21 ("Price Shocks").

### O4 — Do not use media-based signals; no news pipeline now *(book: C2, p. 623)*
The book itself notes that media coverage is a lagging indicator. No work proposed beyond recording B-EVENTS for scheduled events.

### Not applicable
CFTC Commitment of Traders, contrary-opinion polls, Fibonacci retracements and targets, Elliott waves, Gann, astrology.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 shock detector and study | medium | medium | – | low–medium | diagnostics module |
| 2 | O3 stress scenarios | – | **high** | medium | medium | O1 |
| 3 | O2 shock-aware guard | – | medium | – | low | O1 |
| 4 | O4 no media signals | – | – | – | none | – |

## 5. Affected files
`analytics/domain/` (true range, volatility ratio, event study), diagnostics endpoint, `risk_management/domain/models.py` (optional guard), `backtesting` (stress runner), app diagnostics page, tests.

## 6. Incremental plan
1. True-range and ratio functions; event study report.
2. Stress scenarios from the detected windows.
3. Optional guard evaluated through the pipeline.

## 7. Acceptance criteria and tests
* Ratio matches hand computation; injected shocks are detected at threshold 3; event study counts per class sum correctly.
* Guard off by default; risk behaviour unchanged unless enabled; ruff, mypy, tests green.

## Caveats
The corn and bond study numbers date from 1960–1990s and the author notes the lags vary with the state of the economy. Nothing in the read pages shows an exploitable post-shock pattern in crypto.
