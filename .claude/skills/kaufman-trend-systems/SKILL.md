---
name: kaufman-trend-systems
description: Trend-following system design from Perry Kaufman's "Trading Systems and Methods" (5th ed.) ch. 7-9 and 17 — why trend systems work and what their profile looks like, moving average vs exponential smoothing (alpha, residual impact), signal definitions, entry timing consistency, bands and channels to cut false signals, comparison of six trend methods, choosing speed, momentum and RSI as timing tools, efficiency ratio, KAMA and other adaptive filters, and noise-based market selection. Use when designing or reviewing a trend/breakout bot, choosing an MA/EMA/KAMA period, setting breakout bands, or deciding if a market/timeframe suits trend-following.
---

# Trend systems and adaptive filters (Kaufman, *Trading Systems and Methods*, ch. 7-9, 17, 23)

Page numbers are book pages (the PDF is the book + 20). **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (futures and stocks; mostly daily bars, many tests without costs; the book's authors' own methods such as KAMA are the author's). Chapter analyses: `docs/books/04-trading-systems-and-methods-kaufman/ch07-*.md`, `ch08-*.md`, `ch09-*.md`, `ch17-*.md` (each notes which pages were only partly read). Companions: `chan2-momentum`, `kaufman-system-testing`, `kaufman-risk-sizing`.

## 1. Why trend systems work and what they look like (pp. 309-313, 317-320)
- Long trends come from slow, persistent fundamentals; price runs have a **heavy tail** (more long runs than coin flips). Trend methods **do not work without trend**; they differ in risk profile and trading frequency, not much in long-run return.
- **Profit tail**: results per trade have a long right tail and short left tail; one big gain can cover 30+ small losses.
- A healthy profile (NASDAQ-100 futures, 40-day MA direction, 10 years, no costs): ~150 trades, **34.7% winners**, winners held **31.65 bars vs 6.64** for losers, **10 consecutive losses**. In general **< 30% hit rate is common**. Taking profits early or adding stops "reduces or eliminates the chance of capturing the heavy tail" (author's warning) (pp. 317-320).
- Trends are clearer at lower frequencies; **fast trends are less stable**; rates/FX trend cleaner than single stocks; liquidity helps (p. 313).

## 2. Smoothing mechanics (pp. 279-304)
- Trend filters trade **lag for noise**: lag is a zone of uncertainty that lets you ignore noise; cutting it adds false signals; best historical results often come from overfitting (p. 280). There is no "correct" trend, only benefits and trade-offs; predictive models degrade when extrapolating outside the historical range (p. 279).
- **Exponential smoothing**: `E_t = E_t-1 + a*(p_t - E_t-1)`, `E_1 = p_1`. Day conversion `a = 2/(n+1)` (Hutson) leaves a constant **13-14% residual impact** of old data; general `c = 1 - RI^(1/n)`. EMA never discards old data, so "10%" smoothing is slower than a 10-day MA; EMA turns **one period after the peak** on a ramp where a 5-day MA settles with lag 1 (pp. 293-299).
- **Drop-off effect**: simple MAs and regressions jump when old data leaves the window; front-weighting and exponential smoothing reduce it (p. 293).
- **Reduce lag**: error-correcting smoothing (smooth the lag `e_t = p_t - E_t` and add it back); double smoothing slows the line; Blau double smoothing of price changes (e.g. 250/5) recovers speed but leaves the price scale (pp. 301-304).
- **Test-grid distribution**: space smoothing constants (or periods) geometrically, not equally (pp. 299-301).

## 3. Signals and entry timing (pp. 314-318)
- Signal by **line direction** vs **price crossing the line**: direction gave 26-37% fewer trades and better results in the author's example; periods were **doubled** (5, 10, 20, 40, 80) to keep percentage changes comparable. On the fastest window price penetration lost less.
- **Consistency between test and live**: a signal computed at the close implies entry at that close; waiting for the next open is trading differently from the test. Either compute just before the close, or **project the price that would trigger the signal** and place a stop order early. Entry-delay study: low-noise Eurodollar worsened with delay; noisy S&P improved entering at the next open/close except on 5-day windows.

## 4. Bands and channels (pp. 320-323)
Bands cut trades without sacrificing the biggest gains: high-low ranges, Keltner, percent bands, absolute points, volatility bands scaled by percent of line, ATR or standard deviation. In **trending Eurodollar** waiting for a band cross hurt; in noisy S&P it helped (made the 40-day system profitable). Percent bands fail with back-adjusted series that go negative.

## 5. Comparison of six trend methods (pp. 336-347, 359-361)
Momentum, simple MA, exponential smoothing, N-day breakout, swing breakout, regression slope; always in market, no stops, entry at the close, US$20/futures trade and US$0.01/share costs, 20 years, periods 5...160. Findings: long-term trend is profitable; all basic systems profit if the market trends; profit factor improves with period; MA often best; **breakout makes less than half the trades**, has the higher hit rate (just under 50% vs ~34% for MA/momentum and ~43% for slope/EMA), the highest average profit per trade **and the highest risk**; short periods mean more trades, lower profit per trade, higher cost sensitivity: **periods with more than 200 trades in twenty years did worse**. Net return differences between methods are small; the real differences are frequency, size of return and risk per trade.
- **Speed**: a rule of thumb is to use a calculation period of about **one quarter of the swing you want to capture** (a 3-month swing -> a 16-day MA); a "best" period over six months or more may only mean a seasonal move was missed. Multi-average example (Eurobund): MA 80 PF 1.88; 40/80 cross 1.45; 20/40/80 PF 2.80 (one market).
- Robust pattern to expect (Krausz-derived, pp. 838-841): in a trend system, longer periods give higher profit per trade, higher reliability and proportionally fewer trades; per-trade returns should form a **continuous pattern** against average holding time. Use this as a sanity check on test results.

## 6. Momentum and oscillators as timing tools (pp. 369-379, 385-389, 426)
- Momentum `M(n) = p_t - p_t-n`; it is **not volatility** (round trip = zero momentum, high volatility). Crossing zero is basically the same as the MA turning. Window: sample values or mark peaks/troughs and use half to twice the average peak spacing. Use momentum/oscillators mainly for **timing inside a larger trend** (a 6-day momentum inside a 30-50 day trend gives entries within ~3 days).
- Extremes: thresholds as a multiple of the indicator's standard deviation (2 sigma ~ 5% beyond); fixed thresholds drift because **momentum scale changes with volatility**. Exits range from the opposite signal to **zero momentum** (reversion premise) to letting it run.
- **Wilder RSI**: 14-day, 30/70 limits; data show tops/bottoms near **72 and 32**, so 70/30 are "too close to select"; **1.5 standard deviations** is suggested as a compromise. Variants: n-day-change RSI, RSI-change contrarian, CMO, 2-day RSI.
- Closing advice (p. 426): momentum used **against** price direction is high risk; use it as a **timing tool inside a trend strategy** ("buy dips, not highs"), tuning the period so extremes occur at the desired frequency.

## 7. Adaptive techniques (pp. 779-798)
- **Efficiency ratio** `ER_t = |p_t - p_t-n| / sum|p_i - p_i-1|` (noise measure; n ~ 8-10). **KAMA**: `KAMA_t = KAMA_t-1 + sc_t*(p_t - KAMA_t-1)`, `sc_t = [ER_t*(fastest - slowest) + slowest]^2`, `fastest = 2/(2+1)`, `slowest = 2/(30+1)`. Squaring makes the slow end extremely slow (~900 periods) and the fast end like a 4-5 period trend. Practical rules: add a small filter on minimum average change, a **small filter on direction changes (e.g. 0.1 std of line changes)**, trade the **direction of the line**, keep `n` below 14, upper limit 30 (p. 779-783).
- Comparison 1990-Jul 2011, 15 futures, before costs: average profit factor **KAMA 1.53**, MAMA 1.36, correlation 1.22, VIDYA 1.17; fewer trades with better results; S&P results weak. Caveat: KAMA is the **author's own method**, and a fair comparison with a fixed MA needs periods sampled geometrically over its 25-900 range (pp. 786-788).
- Other: Ehlers fractal adaptive MA and MAMA/FAMA, Chande VIDYA, correlation (r^2) adaptive; adaptive momentum/RSI/stochastic; McGinley Dynamic `MD_t = MD_t-1 + (p_t - MD_t-1) / (k*n*(p_t/MD_t-1)^4)`, `k = 0.6`. Adaptive process by retesting on recent data: "the faster you react, the less data you have to decide" (pp. 788-798).

## 8. Market selection by noise (pp. 1070-1072)
Using the 65-day ER: profit factor of a 65-day MA tends to rise with average ER (Eurodollar 0.1816 -> 2.43; S&P 0.1203 -> 1.16; several stocks/commodities near or below 1). Low-ER markets suit mean reversion; **do not include markets incompatible with the strategy's nature**.

## 9. [Adaptation] Using this in the bots
1. Compute ER per symbol/timeframe and enable trend bots only where ER is historically high enough (validate out of sample); route low-ER symbols to reversion strategies.
2. Use a geometric period grid with <= 4 variables; start from period ~1/4 of the swing and compare EMA vs KAMA only with equally distributed fixed-period baselines.
3. Evaluate as a trend profile: expect low hit rate, winners held longer, long losing streaks; do not tune it into a high-hit-rate system with early profit-taking.
4. Compute the signal on the closed candle and enter at the next open unless a pre-computed stop-entry is built and tested identically.
5. For perps, note funding costs for the crowded side and gaps through stops during liquidation cascades; the book's costs are futures-specific.
6. Momentum/RSI as pullback timing inside a trend; thresholds as multiples of the indicator's own standard deviation, re-estimated rolling.
