# Book 2 · Chapter 4 — Mean Reversion of Stocks and ETFs

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 87–106 was read.

The chapter is about US equities and ETFs (shorting, index arbitrage, daily open/close prices, S&P 500 universes). The author again states that **backtests exclude transaction costs and use survivorship-biased data**, and that the open/close prices used are consolidated, so real results "will be lower" (p. 88). Most content does not transfer to a spot long-only crypto system; the transferable ideas are listed explicitly.

## 1. Chapter summary (pp. 87–106)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Individual stocks almost never meet the stationarity definition; **stock pairs found cointegrated in one period often stop cointegrating out-of-sample** because company fortunes diverge. Trading many pairs only helps if the out-of-sample expected return per pair is positive; the author found that the losses of "bad" pairs overwhelm the small profits of "good" ones. Extra stock-pair frictions: short squeezes and recalls, uptick rules, tiny displayed quote sizes (an NBBO of 100 shares). Pair trading was more profitable when markets were less efficient and before decimalisation. | Why classic pairs stopped working. | 89–91 |
| C2 | **ETF pairs and triplets** are more robust because the economics of a basket change slowly (EWA/EWC; commodity ETF vs producers). GLD/GDX cointegrated 2006–14 Jul 2008 (99%) and not afterwards; adding the oil ETF USO restored cointegration over 2006–2012, consistent with high oil prices raising mining costs. Lesson: **when a strategy stops working, form a hypothesis for why and test it empirically**; add a rule to stop trading the pair when oil exceeds a threshold. An ETF that holds futures (USO) is not the spot commodity (roll returns, Chapter 5). | Pair selection and failure analysis. | 91–92 |
| C3 | **Buy-on-Gap** (intraday seasonal mean reversion): at the open choose stocks whose return from the previous low to today's open is below −1 standard deviation (90-day close-to-close), **but whose open is above the 20-day moving average** (a momentum filter on a mean-reversion model: small drops revert, large drops are often news), buy the 10 worst, sell at the close. Backtest APR 8.7%, Sharpe 1.5 (2006–2012, no costs, survivorship bias); the version without rule 2 suffered diminishing returns from 2009; "signal noise" because the open price is not known before the open. Short-on-gap mirror: APR 46% but a steeper drawdown. Lesson: series that don't mean-revert in daily bars can revert during **specific periods**. | Finding seasonal reversion. | 92–96 |
| C4 | **Index/ETF arbitrage**: stocks vs index futures have become too tight; selecting a *subset* of stocks (those that individually cointegrate with SPY, 98 stocks, then re-tested together) widens the spread; linear strategy (look-back 5, chosen with hindsight) APR 4.5%, Sharpe 1.3, decaying because hedge ratios were not retrained. Johansen accepts at most 12 series. | Exploiting a basket vs its index. | 96–102 |
| C5 | **Cross-sectional mean reversion**: weights `wᵢ = −(rᵢ − r̄) / Σ|rₖ − r̄|`, always $1 gross; parameterless, near dollar-neutral; APR 13.7%, Sharpe 1.3 on S&P 500 (2007–2011); the open-to-close version has APR 73%, Sharpe 4.7 before costs but doubles transaction costs and has signal noise. Profits arise only in aggregate across stocks. Other ranking variables (P/E) can avoid shorting stocks whose move is explained by fundamentals. | Relative-value over a basket. | 102–105 |
| C6 | Key points include: beware company fundamentals; ETF portfolios over stock pairs; momentum filters improve consistency of reversion. | – | 106 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Pair/ETF cointegration, index arbitrage | n/a | Needs short legs and multi-asset portfolios; one asset per bot, long-only. |
| Out-of-sample failure of fitted relationships | ⚠️ concept applies | Any fitted parameter on a single pair can decay; the system has no way to detect it (no re-estimation, no monitoring of regime). |
| Failure-analysis workflow | ❌ | No place to record a hypothesis for why a strategy stopped working and its test result. |
| Momentum filter on a reversion entry | ❌ | No such strategy; strategy framework supports combining conditions inside one class only. |
| Seasonal / intraday-window behaviour | ❌ | Strategies see only the candle OHLCV; no time-of-day or day-of-week features. |
| Cross-sectional ranking across assets | ❌ | One symbol per bot; no portfolio engine. |
| Signal noise at the open | n/a | Crypto trades continuously and strategies act on *closed* candles, then fill at the next open (modelled); there is no auction. |
| Costs in backtests | ✅ | Always applied (unlike the book). |

## 3. Opportunities

### O1 — "Strategy post-mortem" record and decay monitor *(book: C2, pp. 91–92)*
* **Problem:** the book's most reusable lesson is methodological: when GLD/GDX broke, the author hypothesised oil costs and tested it. We have no structure to capture why a bot or strategy was retired, which hypothesis was tested and what the result was, and no automatic signal that a strategy's recent behaviour left its backtest range.
* **Proposal:** (a) a lightweight note attached to a bot/backtest (free text, audit-logged; ties to book 1 ch. 1 O3 and ch. 6 O6); (b) a **decay monitor** comparing rolling live/paper results with the backtest distribution (reuses book 2 ch. 1 O4 and book 1 ch. 5 O1/O5).
* **Benefit:** institutional memory and early warning for a strategy whose edge is gone. **Complexity:** low for notes, medium for the monitor. **Risk:** a monitor on short samples raises false alarms; show sample sizes. **Validation:** tests with seeded equity series that drift below the backtest range.

### O2 — Momentum (trend) filter option for the future mean-reversion strategy *(book: C3, p. 93)*
* **Proposal:** when book 2 ch. 3 O1 (`bollinger_reversion`) is built, include an optional long-term moving-average filter (enter only if price is above the N-period moving average), mirroring rule 2 of Buy-on-Gap. The book explains the rationale: shallow dips revert, deep drops often reflect news.
* **Benefit:** a research hypothesis worth testing in crypto; **it must be tested**, not assumed. **Complexity:** low (one extra parameter, but another parameter to over-fit). **Validation:** with/without filter on train/test; sensitivity to N.

### O3 — Time-of-day / day-of-week conditioning for research *(book: C3, p. 96 — "seasonality at a short time scale" · crypto application is our adaptation)*
* **Proposal:** extend diagnostics (book 2 ch. 2 O1) to compute mean-reversion/trend statistics **by hour-of-day and weekday** (UTC) for a pair, so the operator can see whether any window behaves differently. The book gives no crypto evidence; this is exploration only. **Complexity:** low–medium. **Risk:** easy to data-mine (24×7 buckets × many pairs); require out-of-sample confirmation and apply the trial-count discipline from book 1 ch. 3 O7. **Validation:** synthetic series with a planted window effect.

### O4 — Cross-sectional ranking across a coin basket *(book: C5, pp. 102–105)*
* **Proposal:** a *research-only* report ranking a set of imported pairs by short-term relative return and testing whether the worst performers bounce (long-only version: buy the bottom-ranked, hold N candles). The current architecture has no multi-asset strategy or portfolio engine, so a trading implementation is out of scope; the research report can use stored candles and the existing metrics.
* **Complexity:** medium for research; very high for trading. **Risks:** the long-only half drops the hedge that makes the book's version near dollar-neutral, so crypto market-wide crashes hit every position at once; survivorship (only surviving coins are imported); correlated assets reduce independence of observations. **Validation:** stats on stored data with held-out period; never presented as a tradable result.
* Record the trading version as **B-MULTI-ASSET** (see backlog).

### Not applicable / deferred
Stock pairs, ETF pairs/triplets, index arbitrage, Johansen limits, short-on-gap, P/E ranking, primary vs consolidated prices, pre-open prices.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 notes + decay monitor | medium | medium | medium | low–medium | book 1 ch. 5 O1, book 2 ch. 1 O4 |
| 2 | O2 trend filter option | low | – | – | low | book 2 ch. 3 O1 |
| 3 | O3 time-window diagnostics | low | – | – | low–medium | book 2 ch. 2 O1 |
| 4 | O4 cross-sectional research report | low | – | – | medium | multi-pair data |

## 5. Affected files
Bots and backtests notes: `bots/application/service.py`, `backtesting/application/service.py`, audit payload, app notes component; diagnostics: `analytics/domain/` (new functions), `market_data/presentation/router.py`; strategy: `strategies/domain/` (future file); app market-data page.

## 6. Incremental plan
1. Notes field on bots/backtests with audit (cheap, supports every later chapter).
2. Decay monitor once parity/Sharpe metrics exist.
3. Window diagnostics and cross-sectional research report once the diagnostics module exists.
4. Trend filter with the future mean-reversion strategy.

## 7. Acceptance criteria and tests
* Notes are stored, audited and never alter trading behaviour.
* Window diagnostics return per-bucket counts and refuse to show a result for buckets below a minimum sample.
* The cross-sectional report is read-only and labelled as research.
* ruff, mypy and existing tests green.

## Caveats
The performance numbers (APR 8.7%, 13.7%, 46%, 73%; Sharpes up to 4.7) are gross-of-cost, survivorship-biased US equity backtests, several explicitly flawed by the author (hindsight look-backs, open-price signal noise). They are not expectations for crypto. The conclusion that ETF pairs beat stock pairs is the author's, for the US market in 2013.
