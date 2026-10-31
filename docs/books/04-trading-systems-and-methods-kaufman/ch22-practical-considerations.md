# Book 4 · Chapter 22 — Practical Considerations

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 983–1015 were read. The last part of the chapter (pp. 1016–1026: remaining trade-offs, trading limits in futures markets, and similarity of systems / impact of technical systems on markets) was **not** read, so nothing is claimed about it.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Use and abuse of the computer**: automate a clean process; development platforms prevent look-ahead ("the software prevents you from looking ahead at tomorrow's price"); use third-party tools (save optimisation tables to a spreadsheet to sort, average and chart); **"too much power"**: throwing indicators into a pot and letting brute force, neural nets or genetic algorithms find the best is overfitting; less power forces reasoning in advance. | Tool discipline. | 984–988 |
| C2 | **Data accuracy and cleaning**: sources differ (highs/lows), decimal-shift errors, mixed scales between vendors. **Daily-data checks**: outliers (>4% from the previous value or a preset percentage), **missing dates** (more than 4 days without data flagged), **open/close outside the high-low range** (impossible, correct or remove). **Intraday checks**: frequency of data vs the average per 5-minute interval (periods without data); large jumps that reverse within seconds (error or an order that could not be absorbed). Dilemma: a system built on clean data may produce many extra signals live from bad prices; sometimes develop on the dirty data to make the system less sensitive. | Data integrity. | 985–986 |
| C3 | **Standard techniques first**: trend speed matters more than the formula; combining a trend with an oscillator for entry timing is a broad concept satisfied by many indicators; learn from standard tools before custom programming. | Avoid needless novelty. | 986–987 |
| C4 | **More data is better** unless a structural change invalidates old data; if old years had low volatility not likely to recur, the strategy "should at least not post losses" there. | History length. | 988 |
| C5 | **Paper trading**: the out-of-sample set is always used more than once, so paper trading is the safest check; **document expectations first** (trade frequency, holding period, percentage of winners, size of profits and losses); in paper trading assume the **worst price of the 5 minutes following an intraday signal** (or the worst of the closing range for close orders); start with a small amount. | Reality check before capital. | 988 |
| C6 | **"It should work but doesn't"**: outcomes: profitable, not profitable, cannot be implemented, takes too long or too expensive; build slowly, prove each piece before adding the next; stop if performance deteriorates as features are added. **Vertical (stepwise) vs integrated** development: in the vertical way the main rule must be profitable alone, then each feature is tested on top; an integrated solution that is profitable only with the filter is either sophisticated or overfit — decide by **comparing the percentage of profitable parameter combinations with and without the feature** (robustness measure from chapter 21). **Transparent vs complex** systems: complex ones are hard to debug and cannot be visually confirmed on a chart. | How to develop and diagnose. | 988–990 |
| C7 | **Isolating problems**: (1) ambiguous rules interpreted wrongly (e.g. "volume confirms" coded as today's volume > yesterday's instead of > 10-day average); (2) the technique does not work in the tested range — negative results are feedback (combine a long trend with a medium one: long finds the direction, medium captures moves within it); (3) works in some markets but not others (similar markets in a sector should behave alike; futures: fixed income longest trends, equity indexes the noisiest); (4) assumptions made on selected data; (5) **ignoring a few large losses** (LTCM: removing the largest historic losses lowered the apparent risk, which justified leverage; "history does not show enough risk"); (6) **misjudging volatility**: same number of contracts in 2000 as in 1996 meant six times the volatility; stops and sizes must adapt; (7) **evolving markets**: more participants add noise, trend systems enter/exit later and show performance decay over long tests. | Debug checklist. | 990–991 |
| C8 | **Simple systems can work** (long-term trend, dual crossover would have exited after the 2000 peak and before 2008) and "being proactive can cause a small opportunity to be missed but can avoid a big loss". | Simplicity. | 992 |
| C9 | **Extreme events**: price shocks are the most likely cause of catastrophic loss and cause the biggest gap between test and real results; **during a shock diversification fails (correlations go to 1)** because money, not fundamentals, moves markets; backtests treat shocks as normal days and **selection is the greatest beneficiary of shocks**, which explains why out-of-sample and live results are worse; four case studies (Gorbachev 1991, UK election 1992, Gulf War 1990–91, 9/11): shocks do not always hurt trend followers; **prices usually change direction after the shock is absorbed**; **volatility always increases**; a 16% OJ jump reversed 15% in two days (2012). Identification: 1-day range ≥ 5× average true range. | Event risk. | 992–997 |
| C10 | **Crisis management**: reserves to survive an extreme reversal usually lower the return below bond yield, so tactics are needed: (1) after a **windfall** from a shock, **exit or reduce**; (2) after a **large loss**, hold expecting a reversal (may take days and raise risk); (3) with adequate reserves add on peak volume or when volatility declines; the trade has already absorbed most of the risk by the time an exit order could be placed. | Rules for shocks. | 997–998 |
| C11 | **System disconnect in a crisis**: trendlines (50/100/200-day) turn down at the lowest price of the 1987 crash and stay out of phase long after; "dogmatically holding a short because the trendline is down puts the trader out of phase with reality"; suspend trend rules, use predefined crisis rules, and **reinitialise the trends** once volatility has dropped. The slow 2008 decline was different (not a single shock) and trend followers profited. | Rules fail during shocks. | 998–1000 |
| C12 | **Theory of runs** (gambling): probability of a run of n is (1/2)^(n+2); in 256 coups expect a longest run of 7–8; each doubling of the number of trials adds 1 to the longest run. **Martingale** (double after a loss) wins a small amount often and risks ruin; the bet-size limit prevents ruin only if the cap on the doubling is above the longest run; **anti-Martingale** (double after wins) wins big if a long streak comes early. | Position sizing by streaks. | 1000–1003 |
| C13 | **Runs applied to trading**: up/down day runs in 15 futures markets (2000–2011) differ from random (DAX has too many 1-day reversals, Eurodollars too few: use waiting vs immediate entry); **Martingale within a trend** (add after a down close in an uptrend, cap at 8 contracts): Eurodollars (very trending) improved the ratio (6.67 → 8.28) while S&P (noisy) did not (ratio 1.18, no improvement; capped version underperformed); **anti-Martingale within a trend**: uncapped version lost money (−16,443) because the largest position got a loss; capped versions at 2/4/8 improved the ratio (10.95, 10.36, 9.81) in Eurodollars but not in the S&P; fractional Martingale (×1.5) and delayed counter-trend entry also described. **Gustafson's persistence rule** (buy after 4 down closes, exit after 5 up closes or 8 days; in-sample 78% winners and $35k profit, longer test 76% and $348k, in a bull market, long only). | Does betting on streaks work? | 1004–1011 |
| C14 | **Selective trading**: discretionary override of system signals usually favours holding losers until profitable; "business principles must take precedence over emotions". **Filtering out losing trades**: multi-indicator or cross-market confirmation produces "the appearance of a very good system" but is an exercise in overfitting; "the simple solution, even with risk larger than we want, is most often the best"; **never mix in black-box systems** you cannot test. | Discipline and overfit. | 1011–1012 |
| C15 | **System trade-offs**: trend following has many small losses and few large wins (30–35% winners normal, 40–45% unrealistic), longer periods capture more of the fat tail but with more lag risk; the sequence of losses is part of the risk; **mean reversion** has many small profits and a few large losses, needs timing, uses defined profit targets and so must not limit the losses; trade-off between entry distance (threshold), opportunity count and risk per trade (figures 22.14–22.15). | Know the style's payoff shape. | 1012–1015 |

Crypto remarks below are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Look-ahead prevention | ✅ (design) | Strategies receive history up to the signal candle; the engine fills at the next open (`engine.py`). A truncation test is still missing (book 1 ch. 3 O2, ch. 17 O2). |
| Candle validation (outliers, missing intervals, OHLC integrity) | ❌ | `market_data/domain/models.py` has no OHLC integrity check; `_check_candles` only requires ≥1 candle; gaps are ignored. |
| Paper trading with documented expectations | ⚠️ | Paper trading and a paper-days gate before live exist; no stored expected profile and no comparison. |
| Pessimistic fills in paper | ❌ | Paper venue fills at the simulated price/slippage; no "worst of the next N minutes" mode. |
| Vertical vs integrated development evidence | ❌ | No robustness-of-filter comparison (percentage of profitable combos with/without a feature). |
| Volatility-adaptive size/stop | ❌ | See ch. 20 O2. |
| Shock detection and crisis rules | ❌ | None. Risk module has `max_candle_range_pct`, `kill switch`, live caps; no volatility-aware crisis mode. |
| Native stops live | ✅ | Live uses exchange stop orders (protects against disconnect but not gaps/slippage beyond the stop). |
| Martingale or anti-Martingale sizing | ❌ | Not present and not recommended (see O6). |
| Discretionary override | ⚠️ | Manual controls exist (stop/pause bot, kill switch); no rule requiring documentation of overrides. |
| Black-box mixing | n/a | Strategies are open code in the registry. |

## 3. Opportunities

### O1 — Candle data quality validator (integrity + gaps + outliers) *(book: C2, pp. 985–986)*
* **Proposal:** a pure function run at import time and before each backtest/sweep that checks: (1) `low ≤ min(open, close)` and `high ≥ max(open, close)`, `low ≤ high`, prices positive; (2) **missing intervals**: consecutive open times must differ by exactly one timeframe step (report each gap with its length); (3) **outliers**: close-to-close moves above a configurable threshold (the book suggests flagging >4% in daily data; for crypto set per timeframe and report counts, since large moves are real); (4) **zero-volume candles** and duplicated timestamps; (5) intraday data-frequency check (candles per hour/day vs expected). Output: a report stored with the dataset hash; backtests state "N gaps / M flagged candles" and can be configured to refuse or warn.
* **Benefit:** garbage-in prevention for every metric and for the evidence pipeline; supports the book's dilemma — develop on realistic (including dirty) data if live data will be dirty; for exchange data the issue is mainly gaps (maintenance windows), not decimal errors. **Complexity:** low. **Risks:** over-flagging genuine extreme moves; the report must not delete data silently. **Validation:** fixtures with known defects (inverted high/low, one missing interval, a decimal-shifted close), exact counts; clean data yields an empty report. Same as the earlier proposals (book 1 ch. 3, ch. 4).

### O2 — Expectation sheet and paper-trading comparison *(book: C5, pp. 988)*
At bot creation (or promotion to paper/live) record an **expected profile** taken from the validating backtest: trades per month, holding period, win rate, average win/loss, maximum drawdown and longest drawdown. During paper trading show actual vs expected and warn if outside a tolerance band (for example, win rate or drawdown beyond the tested range). The paper-days gate already exists; this gives it content. Include the book's pessimistic-fill idea as an optional paper mode (**"worst price within the next N seconds of the signal"** — requires intrabar data; with candles only, use the candle's high for buys and low for sells as an upper-bound cost test). **Complexity:** medium. **Validation:** deterministic comparison on a replay; no live behaviour change by default.

### O3 — Robustness comparison of filters ("vertical development evidence") *(book: C6, p. 989)*
When adding any filter/feature (volatility filter, regime filter, trend confirmation), require a comparison over the same parameter grid: the **percentage of profitable combinations and the average result with and without the feature**. If the filter only helps at one point of the grid, it is overfitting; if it raises the profitable share broadly, it is an improvement. Fits directly in the sweep robustness report (ch. 21 O1) as a "paired sweep" mode. **Complexity:** low–medium.

### O4 — Common-sense debugging checklist and documented rule definitions *(book: C6, C7, pp. 989–991)*
Maintain in `docs/` a checklist for disappointing results: ambiguous rule interpretation (e.g. "volume confirms" must have a precise definition such as "volume > mean of previous 10 candles", stored in strategy docs and tests); wrong parameter range; behaviour across similar assets; assumptions on selected data; large losses ignored; volatility drift; market evolution. Add a "definition" and "example signal" for each strategy parameter in the catalog (`strategies/catalog.py`) so users read the same rule the code runs. **Complexity:** low (documentation + catalog text).

### O5 — Shock awareness: detection, reporting, and a crisis mode design *(book: C9, C10, C11, pp. 992–1000)*
* **Detection and reporting** (low complexity, see also ch. 14 O1 and ch. 21 O5): flag candles with `range ≥ 5 × ATR(10)` and report open positions at those times, the P/L on shock candles, and whether results depend on them.
* **Crisis mode (design only; needs approval)**: predefined rules when a shock is detected while a position is open — (a) if the shock gives a **windfall profit**, reduce or exit (the book's rule 1); (b) if it produces a **large loss** (spot long, price crash), keep the exchange stop in place (the stop already limits the loss), do **not** add to the position, and do not re-enter until volatility normalises (we do not adopt the book's rule 3 "add at peak volume" because it assumes reserves and a reversal that crypto does not guarantee); (c) after a shock, **re-initialise trend indicators** or pause the bot until volatility drops (the book: trendlines are out of phase), with the pause reported through the Notifier.
* **Crypto adaptation:** Long-only spot cannot profit from a downward shock, so the asymmetric part of the book's advice (windfall → exit) applies to upside spikes; for crashes the only defence is position size, stops and being out of the market (book 4 ch. 21: time in market). Native exchange stops can gap through in a crash: size positions with gap loss in mind (existing `max_candle_range_pct` partially covers it). **Complexity:** medium for detection/reporting; high for crisis mode. **Risks:** a crisis mode is itself an untested rule — test it in the shock-adjusted backtest first. **Validation:** synthetic series with planted shocks; stop gaps; re-entry blocked until the volatility condition holds.

### O6 — Do **not** implement Martingale-style sizing; allow only capped anti-Martingale research *(book: C12, C13, pp. 1000–1010)*
* The Martingale (doubling after losses) is a ruin-risk strategy; the book shows capped results that are good only in the extremely trending market (Eurodollars) and not in the noisy S&P, and the cap needs a stake large enough to cover the cap at all times. For a retail spot account, it would increase exposure exactly when the account is losing; **we recommend rejecting it** (consistent with the platform's risk caps).
* The anti-Martingale (pyramiding winners, resetting after a loss) is the pattern of pyramiding in trend following; capped versions improved the ratio on Eurodollars (up to 10.95) but the uncapped version collapsed; the S&P result was poor. If pyramiding is ever researched, treat it as a position-sizing experiment with **a hard cap**, test across several assets and report the sensitivity (the book's own outcome depends on the market's noise). **Complexity:** medium. **Not recommended for now.** The streak statistics themselves can feed diagnostics: ch. 15 O1 (sequence tables) already covers "runs of up/down candles", and the **theory-of-runs table** (expected number of runs of length n for a fair coin) is a useful null model for those tables. **Validation (if ever done):** compare to the expected-runs null; verify that no stake exceeds the cap.

### O7 — Gustafson-style persistence/mean-reversion rule as a hypothesis, not a feature *(book: C13, pp. 1010–1011)*
"Buy after 4 consecutive down closes, exit after 5 up closes or 8 bars" is a stated, simple and testable rule (the rules are given exactly). It is a long-only counter-trend rule built on the equity upward bias of 1982–2001, which the book notes explicitly ("still in the same bull market"). In crypto, test it as **H-DOWN-RUN-BUY** through the full pipeline (best-of-N, cost sensitivity, truncation, locked segment) and expect it to depend heavily on the sample's drift. **Complexity:** low (parameterised mean-reversion strategy already proposed in book 1/2). Do not implement before the pipeline exists.

### O8 — Selective-override log *(book: C14, p. 1011)*
Record every manual intervention (pause/stop bot, kill switch, manual close) with a reason field and show it in the bot history, so discretionary overrides can be reviewed against what the system would have done (the book's warning: overrides tend to hold losers). **Complexity:** low–medium (audit entry type exists? verify: the platform has audit/security logs for auth; check for bot-level actions before designing).

### O9 — Style-aware expectations (trend vs mean-reversion payoff shape) *(book: C15, pp. 1012–1015)*
Show in strategy documentation and backtest views the **expected payoff shape**: trend strategies — low win rate (30–40%), win/loss > 1, long losing streaks; mean reversion — high win rate, win/loss < 1, rare large losses. Add a "losing streak" metric (longest, and distribution of consecutive losses) and use the theory-of-runs probabilities to compute **the expected longest losing streak for the observed win rate and trade count**, giving the user a realistic psychological and capital expectation. **Complexity:** low. **Validation:** closed-form check against simulation.

### Not applicable
Hardware/software shopping, data vendors, futures roll/back-adjustment, tick-data cleaning for open-outcry markets, the specific historical shocks (Gorbachev, UK election, Gulf War, 9/11, OJ), casino roulette arithmetic beyond its use as a null model.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 candle quality validator | very high | – | high | low | – |
| 2 | O9 style-aware expectations + streak metric | medium | medium | – | low | metrics |
| 3 | O4 rule definitions + checklist | medium | – | – | low | catalog |
| 4 | O3 paired sweep for filters | high | – | – | low–medium | ch. 21 O1 |
| 5 | O2 expectation sheet + paper comparison | medium | high | high | medium | metrics |
| 6 | O5 shock reporting (then crisis-mode design) | high | high | – | medium → high | ATR helper |
| 7 | O8 override log | – | medium | medium | low–medium | audit design |
| 8 | O7 down-run hypothesis | low | – | – | low | pipeline |
| 9 | O6 Martingale | – | – | – | – | **rejected** (anti-Martingale research only) |

## 5. Affected files
`market_data/domain/` (validator) and the import path in `market_data/application`; `backtesting/application/service.py` (report data quality); `analytics/domain/` (streak metric, expected losing streaks, paired sweep); `strategies/catalog.py` and docs; `trading` and `reconciler` for expectation comparison and alerts (Notifier); `docs/openapi.json`; app views; tests.

## 6. Incremental plan
1. Validator (O1) with report stored per dataset; metrics O9; catalog definitions O4.
2. Paired sweep and shock reporting (O3, O5 reporting).
3. Expectation sheet and paper comparison (O2) once alerting exists.
4. Crisis-mode design discussion with the user before any code.

## 7. Acceptance criteria and tests
* Validator reports exact counts for crafted defect fixtures and nothing for clean data; reports are deterministic and tied to the data hash; no data is changed.
* Expected longest losing streak matches simulation within tolerance for given win rate and trades.
* Paired sweep reports the share of profitable combinations with and without a feature.
* All new behaviour off or read-only by default; ruff, mypy and existing tests green.

## Caveats
Kaufman's crisis rules (add on peak volume, hold losers after a shock) come from futures with large reserves and assume reversals that happened in his four examples; four examples are not evidence. The Martingale tests use two futures markets only. The "4% outlier" and "4 days without data" thresholds are for daily futures data. Pages 1016–1026 were not read. Several items repeat earlier proposals (alerting, data validation, shock detection, pipeline) and should be merged in the consolidated backlog.
