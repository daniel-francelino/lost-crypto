# Book 4 · Chapter 8 — Trend Systems

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 309–323 (why trends work, basic signals, trend profile, bands), 336–347 (comparison of six trend systems) and 359–361 (comparison of single vs multiple averages, selecting speed) were read. The sections on applications of a single trend, techniques using two trendlines and multiple-average sequences (pp. 323–335, 348–358, 362–368), including the "early exits from a trend" and "projected crossovers" parts, were **not** read in detail and are not summarised. This is the chapter closest to `ema_crossover` and `donchian_breakout`.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Why trend systems work**: long-term trends from slow, persistent fundamentals (interest-rate policy); **fat-tailed price runs** (more long runs than a random coin-flip model: in 100 flips about 6 runs of four and 1–2 of six); "money moves markets" (flows sustain trends). They **do not work when the market is not trending**; most trend methods have about the same returns over time but different **risk profiles and trading frequency**. A trend is relative to horizon and tolerated noise; "a trend exists if you can profit from it with a trending strategy". | Premise and limits. | 309–311 |
| C2 | **Fat tail in profits**: histograms of per-trade results of a 40-day MA system on bonds, S&P, euro, crude and gold are long to the right and short to the left; one large profit can offset 30+ small losses ("the S&P has relatively smaller fat tails than other markets"). | Shape of trend-system results. | 311–312 |
| C3 | Trends are clearer at lower data frequency; **fast trends are less stable and inconsistent**; interest-rate and FX trends are cleaner than single stocks; liquidity matters for steady trends; emerging markets are trendy until the public brings noise. Select markets and time frames that work with you (longer calculation periods, lower frequency, closer link to fundamentals perform better). | Where trend following fits. | 313 |
| C4 | **Basic signals**: price crossing the trendline vs trendline direction; close-based confirmation; the trendline direction gives **26–37% fewer trades** and mostly better results on Amazon (periods 80, 40, 20, 10, 5: periods **doubling** to keep the percentage change); for the fastest period (5 days) the price-penetration signal lost less (the lag of the trendline is a burden). | Signal definition. | 314–316 |
| C5 | **Consistency of testing and trading**: signals computed on the close imply entry on the close; waiting for the next open means trading differently from what was tested; the practical fix is to compute just before the close or to precompute the price that would trigger the signal (for an MA: the new value is above the old if today's price exceeds the price dropped `n` days ago) and place stop orders in advance. **Entry delay study** (Eurodollar vs S&P, 10 years): Eurodollar (low noise) is best entering on the signal close and worse when delayed; S&P (noisy) improves when entering on the next open or close except at 5 days. | Entry timing and latency. | 316–318 |
| C6 | **Typical trend-system profile** (NASDAQ 100 futures, 40-day MA direction, 10 years, no costs): 150 trades, **34.7% winners**, win/loss ratio quoted as 2.22 (the extracted table text lists average win 1,424.71 and average loss 41.28, which does not match that ratio, so at least one number is garbled in the PDF text; only the ratio is used here), winners held **31.65 bars vs 6.64** for losers, **10 consecutive losses** vs 6 wins. General profile: often under 30% winners; winners must be much larger than losers; winners are held longer; long losing streaks. Adding profit-taking or stops "reduces or eliminates the chance of capturing the fat tail" (this is the author's warning about changing the profile). | What a healthy trend system looks like. | 317–320 |
| C7 | **Bands and channels** slow trading without sacrificing the largest profits: highs/lows bands, Keltner (centre moving average ± average of H, L, C range), percentage bands, absolute-point bands, volatility bands with scaling `s` (percentage of trendline or price, ATR, standard deviation). Results: for **Eurodollar (trendy)** entering on a band penetration is worse; for the **S&P (noisy)** waiting improves results (turns a loss into a profit at 40 days). Percentage bands are wrong on back-adjusted futures that go negative. | Whipsaw reduction. | 320–323 |
| C8 | **Comparison of six systems** (momentum, simple MA, exponential smoothing, N-day breakout, swing breakout, linear-regression slope), always in the market, no stops, entry at the close, $20 per futures trade and $0.01 per share, 20 years, periods 5…160 (the author notes doubling periods 5, 10, 20, 40, 80, 160 would give a better sample). Findings: long-term trend following is profitable; **all basic trend systems are profitable if the market trends**; profit factors improve as the calculation period grows; moving average often best; **breakout has fewer than half the trades**, the highest share of winning trades (~just under 50% vs ~34% for MA/momentum, ~43% for slope/EMA), the largest average profit per trade and also the largest risk; shorter periods give more trades, smaller profit per trade and more sensitivity to costs: **periods that produced more than 200 trades in 20 years were worse**. Differences in net returns across methods are small; the real differences are trade frequency, size of returns and risk per trade. | Trade-offs between methods. | 336–347, 360 |
| C9 | **Selecting speed**: the right speed depends on the user (a fund entering monthly vs an active trader); computer search can overfit (3-day vs 20-day, execution costs dominate); a "best" period of six months or more may only reflect failing to capture a seasonal move; a rule of thumb: mark the swings you want to capture, take the average swing length, and use a calculation period of **about one quarter of the swing** (IBM example: 3-month swing → 16-day MA; 36 trades, 20 profitable, no costs). Multiple-average example (Eurobunds): 80-day MA PF 1.88, 40/80 crossover 1.45, 20/40/80 PF 2.80 (single-market table). | Choosing the parameter sensibly. | 359–361 |

All results are futures/stock tests, many without costs. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Two trend rules | ✅ | `ema_crossover` (two exponential trendlines) and `donchian_breakout` (N-bar channel with separate exit channel). |
| Single-trendline direction rule / price-vs-trendline | ❌ | Not offered. |
| Bands (ATR, percentage, standard deviation) around a trendline | ❌ | None. |
| Trend profile statistics (average bars in winners/losers, win/loss ratio, max consecutive losses) | ⚠️ | `win_rate`, `profit_factor`, `avg_trade_pnl` exist; no average hold time by outcome, no payoff ratio, no consecutive streaks (also book 4 ch. 3 O1). |
| Entry timing consistent with testing | ✅ | The engine fills at the next candle's open, and the live trader acts on closed candles; test = trade by construction (book 1 ch. 5 C1). |
| Execution-delay sensitivity | ❌ | Not computed. |
| Precomputing the trigger price and resting stop orders | ❌ | The live trader reacts after the candle closes; no resting entry orders. |
| Speed-selection aid | ❌ | None. |
| Parameter grids doubling periods | ❌ | Not provided (book 3 ch. 8 O1, book 4 ch. 7 O1). |
| Trade-count awareness | ⚠️ | `fills`/`round_trips` shown; no guidance (>200 per 20 years in the book's setting). |
| Multi-average crossover (20/40/80) | ❌ | Two EMAs only. |

## 3. Opportunities

### O1 — Trend-profile metrics: payoff ratio, average bars in winners vs losers, maximum consecutive wins/losses *(book: C6, pp. 317–319)*
* Compute and show the Table 8.4 set for each backtest: winners count and rate, average win, average loss, **win/loss ratio**, **average holding bars for winners and for losers**, longest winning and losing streaks. Add the book's expectation as helper text: a trend system with ~35% winners needs an average win/loss ratio above 100/35 to be profitable; show the **required ratio** next to the actual one (this is the same arithmetic as the breakeven win rate in book 4 ch. 3 O1).
* **Why:** these quantities let the operator see whether a bot's behaviour matches its design (a "trend" bot that holds winners and losers equally is suspicious) and prepare for the losing streaks psychologically; streaks feed the risk-of-ruin discussion (ch. 22–23). **Complexity:** low (pure functions on round trips with bar counts; needs the entry/exit bar index in the round-trip record, derivable from fill times). **Validation:** hand fixtures reproducing Table 8.4 style numbers.

### O2 — Execution-delay sensitivity *(book: C5, pp. 316–318)*
* **Proposal:** a backtest option that delays fills by `k` candles (k = 0 is the current next-open behaviour, k = 1, 2…) and reports the effect on return and profit factor, to quantify how dependent the strategy is on immediate execution. The book's finding is market-dependent (trendy markets suffer from delay, noisy ones may gain), so the result has to be measured per pair/timeframe.
* **Benefit:** a direct robustness test for latency, queueing, rate limits and operator downtime; cheap to implement in the engine (shift the pending signals). **Complexity:** low. **Risks:** reflects bar-level delays only; at 1m bars a delay of several candles is large relative to real latency; interpretation caution. **Validation:** a strategy whose edge disappears with delay must show it; k = 0 equals the current result bit for bit.

### O3 — Hysteresis band around the trendline (ATR / percentage / standard deviation) as an option *(book: C7, pp. 320–323)*
* **Proposal:** optional `band_multiple` for `ema_crossover` or the fast EMA vs slow EMA gap: enter long only when the fast EMA exceeds the slow EMA by more than `s ×` a volatility measure (ATR or standard deviation of closes), exit when it falls below (maybe at zero or a smaller band). The book shows bands help noisy series and hurt trendy ones, so the benefit must be conditioned on noise (book 4 ch. 1 O1/O2). Default off.
* **Risks:** one more parameter (N increases); delays entries; results are market dependent in the book's own tests. **Validation:** truncation test; effect on trade count (should fall); effect on the profile statistics (win rate up, payoff ratio change). Hypothesis **H-TREND-BAND**.

### O4 — Single-trendline direction signal *(book: C4, pp. 314–316)*
* **Proposal:** a mode in which the signal is "EMA slope turns up/down" (trendline direction) instead of a crossover of two EMAs; per the book this yields roughly 26–37% fewer trades than a price-crosses-trendline rule (Amazon, 10 years). Our dual-EMA crossover already reduces whipsaw relative to price-cross; whether a slope rule differs is empirical. **Complexity:** low. Possible duplicate of existing behaviour (high correlation with a very slow EMA vs fast EMA): check effective N (book 3 ch. 6 O4) before adding.

### O5 — Doubling-period grid presets *(book: C4, C8, pp. 315, 337)*
Same as book 3 ch. 8 O1 / book 4 ch. 7 O1: the author himself uses 5, 10, 20, 40, 80, 160 to keep the percentage change constant and avoid weighting very similar long periods. Provide this preset. **Complexity:** trivial.

### O6 — Speed selection aid: average-swing rule of thumb *(book: C9, pp. 360–361)*
Offer a helper that detects swings on the stored candles (swing filter; book 4 ch. 5) and proposes a calculation period of about a quarter of the average swing length, together with the warning that a "best" period longer than a quarter of the trend's duration implies the strategy missed it. This gives a **non-optimised** starting point (no search over performance). **Complexity:** medium (swing detection). **Risks:** the swing threshold is itself a parameter; the one-quarter rule is the author's rule of thumb from one stock example.

### O7 — Respect the profile: do not graft stops and profit-taking onto trend strategies without measuring *(book: C6, pp. 319–320)*
The author warns that stops and profit-taking can destroy the fat-tail capture. The system already provides optional `stop_loss_pct`/`take_profit_pct` on both strategies. Add to the strategy form's help text and to the red-flag block: if a tight `take_profit_pct` is set, compare with the version without it (a one-click "ablation" run that disables each optional rule and reports the delta). Complexity: low–medium. The ablation view directly implements the book's guideline "prove that each added feature improves results" (ch. 1 and ch. 8). **Validation:** ablation run reproduces the base result when nothing is enabled.

### Not applicable
Futures contract mechanics, back-adjusted data issues, swing and point-and-figure methods (not read), Raschke's first-pullback entry (not read in detail).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O5 doubling-period presets | medium | – | – | trivial | – |
| 2 | O1 trend-profile metrics | high | medium | – | low | round-trip bar counts |
| 3 | O2 execution-delay sensitivity | high | medium | medium | low | engine change |
| 4 | O7 ablation runs | high | – | – | low–medium | – |
| 5 | O3 hysteresis band (experiment) | medium | – | – | low–medium | ATR helper, pipeline |
| 6 | O6 speed aid | low | – | – | medium | swing detection |
| 7 | O4 slope signal | low | – | – | low | effective-N check |

## 5. Affected files
`analytics/domain/metrics.py`, `backtesting/domain/engine.py` (optional fill delay), `backtesting/domain/models.py` (config), `backtesting/application/service.py` (ablation/sensitivity jobs), `strategies/domain/ema_crossover.py` (optional band), indicator helpers, `docs/openapi.json`, app backtest form and detail, tests.

## 6. Incremental plan
1. Grid preset and profile metrics.
2. Delay option in the engine with tests (k = 0 identical).
3. Ablation runner.
4. Experiments with bands and slope signals through the pipeline.

## 7. Acceptance criteria and tests
* With delay 0 the engine's output is unchanged (regression test against existing results).
* Profile metrics reproduce hand calculations; streaks and hold times correct on fixtures.
* New strategy options default off; ruff, mypy, all existing tests green.

## Caveats
Every performance figure is from futures/stock tests (many without costs, 1990–2011), often one market per claim. The statement that most trend methods have "about the same returns" is the author's observation, not a proof. Win rates of 30–35% in a trend profile are a property of those tests; crypto may differ.
