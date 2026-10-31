# Book 4 · Chapter 16 — Day Trading

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 737–745 (costs, strategies, missed orders, slippage estimation, key elements), 759–761 (opening range breakout) and 775–777 (intraday price shocks) were read. The price-pattern systems of pp. 746–758, the rest of the opening-range-breakout material (761–774), intraday volume patterns (774–775) were **not** read in detail and are not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Day trading is hard: intraday prices respond to noise (reports, large orders, analyst changes), not fundamentals; it requires discipline and punishes bad habits; day traders may target about 1¢ per share. | Realistic expectations. | 737–738 |
| C2 | **Transaction costs are the greatest deterrent**: fees plus slippage; improving performance means lower commissions, selecting opportunities carefully (higher volatility makes costs smaller as a percentage) and better execution. Futures/stock volatility and volume tables (1995–2010). The S&P's **open-to-close range is only about half of the day's total range**. | Cost and opportunity. | 738–740 |
| C3 | **Cost depends on strategy type**: trend/momentum entries pay slippage (at least ½ point on the E-mini); the illustrative day: range $931, $10 fee per side, $100 slippage → $821 left; with 1/3 winners and winners twice the losers the net result is minus the total costs ("break-even at $90 for two losses of $45"): **a day-trading trend system must do better than the average trend system to survive**. **Mean-reverting strategies have conservatively about 50% of the slippage** of trend programs, and may earn liquidity rebates. | Which style survives costs. | 740–742 |
| C4 | Choose markets with **high volume and high volatility**; thin markets show larger moves but market and stop orders get poor fills, limit orders may not fill. | Liquidity selection. | 741 |
| C5 | **Missed orders ("unables")**: on news jumps trend-following orders cannot be filled near the system price; skipped trades remove profits but never losses; with 10% unables the profit factor fell from 1.66 to 1.50 in the author's example (5 profitable trades missed per 100, $1,250). | Backtest optimism from missing fills. | 742–743 |
| C6 | **Estimating slippage**: depends on volatility, overall volume, order size and market activity; record order price, execution price, volatility, volume, time of day and tick volume and fit `slippage = a0 + a1·volatility + a2·daily volume + a3·time-of-day factor + a4·order size`; Greer & Brorsen found large stop orders had modest slippage; **volatility-adjusted slippage**: scale the assumed slippage up with volatility, **never below a minimum**; "be conservative". Use trade-on-settle orders for closing. | Calibrating cost. | 743–744 |
| C7 | **Evolution**: opening-range breakouts (1990s) → pairs trading (2000s) → high-frequency (now); trend methods are not used for holding periods under 3 days and "probably do not apply under 20 days" (the author's statement); short-term movement is mostly noise, so **wait for pullbacks on directional entries; mean reversion is preferred**; classic chart patterns on intraday data are "simply random patterns". | Style migration. | 744–745 |
| C8 | **Opening range breakout** (buy when price moves a set distance above the open, reverse below; exit at the close), improved by conditioning on an inside day (Crabel: % profitable rises, e.g. bonds 60% → 76%) — figures from 1989–1990 that "cannot be reproduced exactly" today; fixed-point breakout sizes should be replaced by volatility-based ones. | Intraday breakout. | 759–760 |
| C9 | **Intraday price shock strategy** (fade the reaction): shock = bar with true range ≥3× the previous average bar (or ≥2× the average of the same bar over past days, comparing against the same time-of-day, since spikes occur at the open); if the shock bar closes in the top 20% of its range, sell short at the next bar's open (and symmetrically buy); no stop for two bars, then a stop beyond the extremes of the three bars; exit at the close; "a larger-than-normal move will more often be caused by noise and will tend to reverse"; profitable in gold (20-minute bars) and 30-year bonds in the author's tests; floor-trader volume exit idea. | Fading intraday shocks. | 775–777 |

Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Costs always included | ✅ | `fee_rate` and `slippage_bps` always applied. |
| Slippage varies with volatility/size/time | ❌ | Constant `slippage_bps` (also book 2 ch. 7 O2, book 1 ch. 5 O4). |
| Minimum slippage floor when scaling | n/a yet | No scaling exists. |
| Missed orders ("unables") in backtests | ❌ | Every signal fills at the next open in the engine; failure modes exist only live (rejections are counted: `rejected_signals`, e.g. "already in position"). |
| Cost impact by strategy type | ❌ | One slippage for all. |
| Mean reversion cheaper to execute (limit orders) | ❌ | Limit-order simulation does not exist; paper venue simulates market fills. |
| Intraday timeframes | ✅ | 1m/5m/15m/1h supported; the crypto market is continuous so "open-to-close" and "opening range" do not exist naturally. |
| Missed-fill reporting in paper/live | ⚠️ | Orders can be rejected or unfilled; no summary of missed profits vs avoided losses. |

## 3. Opportunities

### O1 — Missed-fill (“unables”) sensitivity in backtests *(book: C5, pp. 742–743)*
* **Proposal:** a deterministic option that drops a fraction `u` of **profitable** entries chosen by an unfavourable rule (for example the entries that occur on the largest bars) or, more simply, entries on candles whose range exceeds a percentile of the recent range, and reports the effect on profit factor and return. The point is to quantify how fragile the result is to being unable to fill during fast moves. The author's own example turned profit factor 1.66 into 1.50 at 10% unables.
* **Benefit:** a robustness figure for trend strategies that enter on breakouts, where fast candles are exactly when fills are worst. **Complexity:** low–medium (engine option, deterministic selection). **Risks:** the selection rule is ours; it only approximates real unfilled orders. **Validation:** the fraction removed matches `u`; `u = 0` reproduces the current result.

### O2 — Volatility-scaled slippage with a floor, calibrated from recorded fills *(book: C6, pp. 743–744)*
Same direction as book 2 ch. 7 O2 and book 4 ch. 8; adds the author's two rules: scale slippage with current volatility, **cap the reduction at a minimum**, and prefer fitting `a0…a4` on recorded executions (book 1 ch. 5 O4). Provide the regression as an analysis report once enough fills are recorded. **Complexity:** medium.

### O3 — Strategy-type-specific cost assumptions *(book: C3, pp. 740–742)*
Allow separate slippage assumptions for entries that pay the spread (breakout/trend, market orders) and for limit-style entries (mean reversion); document that the book's conservative estimate is 50% for mean reversion and that this needs a limit-order simulation to be honest (a limit order may not fill: opportunity cost, book 1 ch. 2 C7). **Complexity:** medium; depends on a limit-order paper venue.

### O4 — Cost coverage guard per timeframe *(book: C2, C3, pp. 738–741)*
Warn when a configuration's average gross profit per trade is below a multiple (for example 3×) of the round-trip cost, in particular for 1m/5m timeframes (book 4 ch. 5 O6 covers the metric). In the UI, show the break-even calculation from the book's example (win rate, payoff ratio, cost per trade) so users see why a 33%/2:1 system loses its edge to costs on short horizons. **Complexity:** low.

### O5 — Shock-fade as an experiment (not a recommendation) *(book: C9, pp. 775–777)*
The volatility-ratio detector (book 4 ch. 14 O1) plus a rule "shock candle closing in its upper/lower 20% → trade against it for the next candle(s)" is the book's example. For long-only spot only the **buy-the-flush** half is available (shock down closing in the lower 20% → buy next open, stop below the shock extreme, exit after k candles). It is a counter-trend entry in the dangerous direction for crypto crashes. **H-SHOCK-FADE:** run through the pipeline only after shock diagnostics (ch. 14 O1) show a reversal tendency on the chosen timeframe. **Complexity:** low–medium.

### O6 — Time-of-day-aware volatility/volume baselines *(book: C9, p. 775)*
Reinforces book 4 ch. 12 O1: comparing a bar with the average of the *same* time-of-day bar avoids treating the open/close spikes as shocks. **Complexity:** part of ch. 12 O1.

### Not applicable
Pairs trading and HFT evolution, trading limits and locked-limit days, futures settlement orders, floor-trader behaviour, pit/electronic transitions.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O4 cost-coverage guard | high | – | – | low | metrics |
| 2 | O1 missed-fill sensitivity | high | medium | – | low–medium | engine change |
| 3 | O2 slippage model + calibration | high | medium | – | medium | execution records |
| 4 | O3 type-specific costs | medium | – | – | medium | limit-order venue |
| 5 | O5 shock-fade experiment | low | – | – | low–medium | ch. 14 O1 |
| 6 | O6 baselines | low | – | – | low | ch. 12 O1 |

## 5. Affected files
`backtesting/domain/engine.py` and `models.py` (options), `execution/domain/fills.py` (slippage model), `analytics/domain/metrics.py`, `docs/openapi.json`, app backtest form and detail, tests.

## 6. Incremental plan
1. Cost-coverage guard and break-even helper.
2. Missed-fill option.
3. Slippage model and calibration report once records exist.
4. Experiments through the pipeline.

## 7. Acceptance criteria and tests
* Options default to current behaviour; `u = 0` is bit-for-bit identical.
* Cost guard fires on a configuration with gross profit per trade below the threshold and not on a profitable-enough one.
* ruff, mypy and existing tests green.

## Caveats
Numbers (opening-range win rates, cost examples, evolution of day trading) date from the 1990s–2011 and from futures and US stocks. The statement that trend methods do not apply under 3–20 days is the author's judgement for his markets, not tested on crypto.
