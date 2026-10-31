# Book 4 · Chapter 3 — Charting

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 79–82 and 144–146 were read; the section headings of pp. 83–150 (Dow's bar chart, formations, trendlines, one-day patterns, continuation patterns, accumulation and distribution, price objectives, candlesticks, evolution of patterns) were scanned. The ~60 pages of pattern descriptions were **not read** in detail. Pattern analysis in this chapter is subjective charting, which the project excludes (see [book 3 ch. 1](../03-evidence-based-technical-analysis-aronson/ch01-objective-rules-and-their-evaluation.md)).

## 1. Chapter summary (what was read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Every trading system began with a chart; the system's past signals should always be viewed on a chart ("the appearance of an odd trade can save a lot of aggravation and money"). | 79 |
| C2 | Markets have a "character" (habitual pattern types, e.g. V bottoms in cattle, round tops in cotton, new highs followed by fast pullbacks in the S&P). The author says this about commodities of the 1970s; no evidence is presented here. | 79–80 |
| C3 | Many valid chart interpretations exist for the same chart (frequency, start date, horizon), and published chart analysis may help *cause* the repeating patterns (self-fulfilling behaviour). | 80 |
| C4 | **What causes chart patterns**: human habits, e.g. orders cluster at **round numbers** (even dollars, then 50¢ and 25¢) in both stocks and futures; the public enters at the wrong time ("grand rush"); "lost motion" overshoot of up to about 10%; mass psychology (bubbles and crashes quoted). | 81–82 |
| C5 | Trends are **easier to see in retrospect**; a trend signal arrives at the point of greatest uncertainty; trend followers need to be right only **30–35% of the time** because average wins exceed average losses; long-term trends are more reliable than short-term ones (the daily effect of a long trend is tiny relative to noise); weekly charts reveal trends daily charts hide. | 144–145 |
| C6 | Confirming signals converging at one price carry more weight; **pattern failures** are signals (a failed breakout, "bull/bear trap", is traded the other way: Wyckoff's "effort and results"); a **change of character** (larger reactions inside a trend) signals an exit. | 145–146 |
| C7 | Bulkowski's candlestick findings quoted: best candles close within a third of the bar low, candle patterns perform better in bear markets and on higher volume, unusually long wicks or tall candles outperform. | 144 |

Chapter 4 turns some of these into systems and quotes Bulkowski's rankings.

## 2. Diagnosis (verified in code and UI)

| Concept | Status | Evidence |
|---|---|---|
| View trades on a chart | ✅ | The app's backtest detail shows candles/equity, trades and orders (`candle-chart-rows.ts`, trades tab). Whether signal markers are overlaid on candles is not verified here. |
| Round-number order clustering | ❌ | No consideration in stop or target placement (`stop_loss_pct` is a percentage from the entry close). |
| Win rate as a target | ⚠️ | `win_rate_pct` is a headline metric; `profit_factor` and `avg_trade_pnl` exist but not payoff ratio / expectancy per trade or the breakeven win rate. |
| Pattern failures as signals | ❌ | None. |
| Multi-timeframe confirmation | ❌ | A bot runs one timeframe (see ch. 19). |
| Subjective chart patterns | n/a (excluded) | |

## 3. Opportunities

### O1 — Payoff ratio, expectancy and breakeven win rate beside win rate *(book: C5, p. 144)*
* **Problem:** a trend strategy with a 35% win rate is normal (the book); showing win rate prominently invites the wrong judgement.
* **Proposal:** add `payoff_ratio = average win / average loss`, `expectancy per trade` (net, after costs; already close to `avg_trade_pnl`) and `breakeven_win_rate = 1 / (1 + payoff_ratio)`, plus the sample size. In the app, show win rate next to its breakeven. **Complexity:** very low (pure functions over `round_trip_pnls`). **Validation:** hand fixtures.
* **Caveat:** payoff ratio is itself noisy with few trades.

### O2 — Check that trades are drawn on candles in the app *(book: C1, p. 79)*
Verify that entries, exits, stops and rejected signals are overlaid on the candle chart (bots and backtests) so odd trades are visible. If missing, add markers. **Complexity:** low (frontend chart rows). This is a UX check; the book's recommendation is to look at the chart of past signals.

### O3 — Stop and target placement relative to round numbers *(book: C4, p. 81 · hypothesis)*
* The book states order clustering at round numbers. A stop at an obvious level may be filled with worse slippage (also book 2 ch. 7 stop hunting). **Hypothesis H-ROUND:** test, using realised stop fills (book 1 ch. 5 O4), whether stops/targets at round numbers experience worse slippage than nearby non-round levels, then decide whether to offset them. No change until measured. **Complexity:** low (analysis after data exists).

### O4 — Failed-breakout (trap) rule as a candidate objective strategy *(book: C6, p. 146 · hypothesis)*
An objective definition is possible (a Donchian breakout that returns inside the channel within *k* candles → exit/reverse). Long-only spot can use it as an **exit** rule on the existing Donchian strategy ("exit early if the breakout fails"). **H-FAILED-BREAKOUT:** run as an experiment through the sweep → best-of-N → validation pipeline; no a-priori edge claimed. **Complexity:** low–medium.

### Not applicable
Descriptions of formations, trendline drawing, Dow theory, candlestick names, price objectives from patterns.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 payoff/expectancy/breakeven | medium | – | – | very low | – |
| 2 | O2 chart overlay check | – | – | medium | low | frontend review |
| 3 | O4 failed-breakout experiment | low | – | – | low–medium | book 3 pipeline |
| 4 | O3 round-number study | – | low | – | low | realised slippage records |

## 5. Affected files
`analytics/domain/metrics.py`, `analytics/presentation/schemas.py`, `docs/openapi.json`, app metric cards and chart components (`components/backtests`, `components/bots`), `strategies/domain/donchian_breakout.py` (O4 only), tests.

## 6. Incremental plan
1. Payoff and breakeven metrics.
2. Chart overlay review.
3. Experiments (O3, O4) only after the evidence tooling from book 3.

## 7. Acceptance criteria and tests
* Payoff, expectancy and breakeven win rate match hand calculations; `None` when there are no losses or no trades.
* No change to existing strategy behaviour; ruff, mypy, tests green.

## Caveats
Most of the chapter is subjective charting and 1970s–2000s anecdotes; none of the pattern lore was verified or read. The 30–35% accuracy remark is a general statement about trend systems, not a measured crypto figure.
