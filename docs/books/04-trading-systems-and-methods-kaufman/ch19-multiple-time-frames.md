# Book 4 · Chapter 19 — Multiple Time Frames

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 833–841 were read; the last page (842–844: Pring's KST system and summary) was not read. Krausz's Gann/Fibonacci content (838–841) was read for its structure only; it rests on non-testable geometry and is excluded.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Systems that combine **intraday, daily and weekly** data: use a long time frame to identify the trend (trends are best identified over longer periods) and a short one to choose the entry (needs fast response). A single frame has problems: very short = noise; only weekly = direction but high risk and poor entry. | Trend vs timing. | 833 |
| C2 | **Tuning two frames**: the timing indicator's period must be **much shorter than the trend period**; if the trend trade holds ~23 business days, design the oscillator to give a better entry within the first 3–5 days (10–20%); its own stand-alone profit does not matter, because the profit comes from the trend component; use only the **first** oversold signal after the trend signal. Example (euro, 60-day MA, 3-day stochastic): waiting for oversold turned a $2,075 gain into $6,200 in one trade, but in another trade the entry was worse ("not every entry is better"); a 14-day stochastic gave a delayed entry. Entries against the short move also tend to suffer less slippage. | Pullback timing within a trend (cf. ch. 9). | 833–835 |
| C3 | **Elder's Triple Screen**: three frames related by a factor of about 5 (e.g. hourly, daily, weekly); Screen 1 (weekly): the slope of a MACD/13-week exponential sets the trade direction; Screen 2 (daily): an oscillator (Force Index `= volume × (close − previous close)` smoothed over 2 days, or Elder-Ray bull/bear power vs a 13-day exponential, or a stochastic) finds the dips to buy in an uptrend; Screen 3 (intraday): entry by stop order. **Stop**: below the entry day's low or the previous low, move to break-even as soon as there is room, then protect 50% of the highest profit. | A concrete multi-frame process. | 835–838 |
| C4 | **Krausz's laws** (e.g. "higher time frames overrule the lower ones", "levels of support/resistance converge across frames"): based on Gann geometry and Fibonacci, not testable as stated. **Robust pattern** worth keeping: for a trend system, longer calculation periods give larger profit per trade, higher reliability and proportionally fewer trades, and returns per trade should form a **continuous pattern against average holding period** — an expectation useful to judge test results. | A robustness expectation. | 838–841 |

Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Single timeframe per bot | ✅ (limitation) | A bot has one `timeframe`; `StrategyContext` carries one candle; the trader and the backtester feed one series. |
| Higher-timeframe trend filter | ❌ | Not possible without a second series. |
| Resampling lower to higher timeframe | ❌ | Candles are stored per timeframe as imported; no aggregation helper (`Timeframe` set: 1m, 5m, 15m, 1h, 4h, 1d). |
| Look-ahead protection with multiple frames | n/a | Would need care (use only *closed* higher-timeframe candles). |
| Pullback-entry timing | ❌ | See ch. 9 O1. |
| Stop policy: below entry low, break-even, 50% trailing | ❌ | Stops are a fixed percentage; no trailing stop in `risk_management/domain/stops.py` (static `stop_price`, `take_profit_price`). |

## 3. Opportunities

### O1 — Higher-timeframe trend filter built by aggregating the strategy's own candles (experiment) *(book: C1–C3, pp. 833–837)*
* **Proposal:** let a strategy declare an optional higher timeframe (a multiple of the bot's timeframe; the book suggests a factor of about 5) and let the framework **aggregate closed lower-timeframe candles into closed higher-timeframe candles** inside the strategy state (no second data feed, no look-ahead because only completed higher candles are used). A long-only entry from the base rule is allowed only if the higher-frame trend (EMA slope, or KAMA slope) is up. This stays within the "single candle stream" contract of the trader and the backtester.
* **Benefit:** the book's central multi-frame idea at modest cost; expected to reduce counter-trend entries. **Complexity:** medium (aggregation with alignment to UTC boundaries, warm-up, tests for look-ahead, strategy parameters).
* **Risks:** another parameter pair; delays entries; trend filters often lower trade count; the filter's effect needs the whole evidence pipeline. **H-MTF-FILTER.** **Validation:** the truncation test is essential (aggregation must not use the in-progress higher candle); alignment tests (hourly candles forming exactly one daily candle); effect on trades and drawdown.

### O2 — Trailing stop options (break-even and fraction of peak profit) *(book: C3, p. 838)*
* The book's stop rule has three steps: initial stop below the entry/previous low, move to break-even when possible, then protect 50% of the best open profit. The risk module supports only a fixed stop and target. A **trailing stop** (percentage from the highest price since entry, or the fraction of peak profit) is a standard and testable protective rule and also aligns with ATR-based stops (ch. 20).
* **Caveats:** the book itself (ch. 8) warns that stops and profit-taking can destroy the fat tail of trend systems; therefore compare with and without (ablation run, ch. 8 O7). Native exchange stop orders (live) need a replace-order mechanism to trail. **Complexity:** medium (engine, paper venue and live trader/exchange orders; fill rule for gaps). **Validation:** deterministic unit tests of the trail logic; parity between backtest and paper.

### O3 — Expectation check: returns per trade vs holding period are monotone *(book: C4, p. 838)*
For a one-parameter sweep of a trend strategy, plot net return per trade, win rate and number of trades against the **average holding time**; the book expects a smooth increasing pattern of profit per trade and falling trade count as the period lengthens. A non-smooth result is a warning of overfitting or of a data problem. Extends the sweep-robustness view (ch. 5 O1). **Complexity:** low.

### Not applicable
Krausz's Gann geometry and Fibonacci laws, Pring's KST (not read), the Force Index and Elder-Ray details beyond the idea of a Screen-2 oscillator.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 monotonicity expectation | medium | – | – | low | sweeps |
| 2 | O1 higher-timeframe filter | medium | – | – | medium | helpers, pipeline |
| 3 | O2 trailing stops | – | medium | medium | medium | engine + live design |

## 5. Affected files
`strategies/domain/` (aggregation helper, optional parameters), `backtesting/domain/engine.py`, `risk_management/domain/stops.py` (trailing), `trading/application/trader.py` and the exchange adapter (native stop replacement), app forms, tests (truncation, alignment).

## 6. Incremental plan
1. Sweep expectation view (no strategy change).
2. Aggregation helper with look-ahead tests; filter experiment.
3. Trailing stop in backtest/paper first; live only after parity is proven.

## 7. Acceptance criteria and tests
* Aggregated candles equal a direct import of the higher timeframe over a fixture; the filter never uses an unfinished higher candle (truncation test).
* Trailing stop fills and exits are deterministic and identical in backtest and paper.
* Defaults leave existing behaviour unchanged; ruff, mypy, tests green.

## Caveats
Performance examples are single trades from futures charts. The book offers no aggregate statistics for multi-frame systems in the pages read, so any benefit for crypto is unproven.
