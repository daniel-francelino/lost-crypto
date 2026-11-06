---
name: chan2-momentum
description: Momentum strategy design and testing from Ernest Chan's "Algorithmic Trading" ch. 6-7 — causes of momentum, testing time-series momentum with non-overlapping lookback/holding correlations, the 12-month/1-month rule, alternative entry signals, combining momentum with reversion, cross-sectional momentum and its crashes, intraday gap/news/leveraged-ETF momentum, and why stops fit momentum. Use when designing or reviewing a trend-following/breakout bot, choosing lookback and holding periods, or assessing momentum risk.
---

# Momentum strategies (Chan, *Algorithmic Trading*, ch. 6-7)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (its instruments are US stocks, ETFs, FX and commodity futures). Chapter analyses: `docs/books/02-algorithmic-trading-chan/ch06-interday-momentum.md`, `ch07-intraday-momentum.md`.

## 1. Why momentum exists (pp. 133-134, 155-156)
(1) Persistence of futures roll-return sign; (2) slow diffusion/acceptance of information; (3) forced buying/selling by funds; (4) manipulation by high-frequency traders. Intraday adds (5) **triggering of stop orders** (breakouts). Time-series momentum (own past return predicts own future) vs cross-sectional (relative performance persists).

## 2. Test before you trade (pp. 134-137)
Correlate (with p-value) the return over a lookback window with the return over a future holding window, across a **grid of (lookback, holding) pairs, using non-overlapping samples** (shift by the larger of the two); also correlate the *signs*; Hurst exponent and variance ratio are global tests. Futures TU: best correlation/p-value trade-offs at (60,10), (60,25), (250,10), (250,25), (250,60), (250,120); H = 0.44 and the variance-ratio test did not reject a random walk because momentum and reversion coexist at different horizons. **Prefer the shortest holding period (best Sharpe).**

## 3. Reference rule (pp. 137-141)
Moskowitz et al.: long if the 12-month return is positive, short if negative; hold one month; stagger entries daily in 1/25 tranches. TU: Sharpe ~1, 1.7%/yr on notional, max drawdown 2.5%; BR, HG, TU work (table 6.2). A **lagged roll-return signal** (3% threshold) did better (Sharpe 2.1). Few trades => **data-snooping risk is real**; only out-of-sample counts.
Other entries: N-day new high, price above (exponential) moving average, upper Bollinger band, more up days than down in a window, Alexander filter (enter after +x%, exit after -x% from the high). **Combining reversion and momentum** can help (CL: long if price below its level 30 days ago but above its level 40 days ago; 12% / Sharpe 1.1). The S&P Diversified Trends indicator (long above EMA, short below): Sharpe 1.3, max drawdown -16.6% (1988-2010) but weak since 2008.

## 4. Cross-sectional and event momentum (pp. 141-151)
Futures cross-sectional (rank 12-month returns): 18% / Sharpe 1.37 in 2005-2007, then **-33%/yr in 2008-2009**. Stocks (top vs bottom decile of 12-month returns, hold 25 days): Sharpe 4.1 in 2007, then **-30%/yr in 2008-2009**; long-run Daniel-Moskowitz result 16.7% / Sharpe 0.83 (1947-2007). News-sentiment factors (Hafez & Xie 52-156% before costs) and fund-flow pressure (Coval & Stafford) need expensive data (~$10k/yr) and delays cause slippage.

## 5. Drawbacks and advantages (pp. 151-154)
- **Drawbacks**: harder to make profitable; lower Sharpe because long windows/holds give **few independent signals**; **momentum crashes** after financial crises (after 1929 a strategy needed 30+ years to recover its high); news-driven horizons **shorten as more traders arrive**, with no calendar to adjust holding time.
- **Advantages**: **stops are coherent** (an opposite signal acts as a stop); loss per position is capped by time/stop exit while upside is open; fat tails (high kurtosis) favour momentum (a random series with TU's kurtosis and no autocorrelation matched TU's momentum return in 12% of simulations — so test against that null); diversification across asset classes; **combining momentum with reversion raises Sharpe and cuts drawdown**.

## 6. Intraday momentum (ch. 7, pp. 155-168)
- **Opening-gap strategy**: buy if the open exceeds the previous high by 0.1 x the 90-day std of daily returns; short below the previous low by the same; exit at the close. FSTX 13% / Sharpe 1.4 (2004-2012); GBPUSD with own open/close times 7.2% / 1.3. Hypothesis: after a no-trade period, stops trigger together and cascade.
- **News-driven**: post-earnings drift — enter at the open if the overnight return exceeds half a std in either direction, **without interpreting the news**, exit at the close. S&P 500 2011-2012: 6.7% / Sharpe 1.5, leverage only ~4x; holding overnight had negative average return => the drift horizon shrank to intraday. Macro releases showed no significant EURUSD effect in the author's tests.
- **Leveraged ETFs** rebalance near the close in the direction of the day's move (momentum): buy DRN if return to 15 min before close > +2%, short if < -2%: 15% / Sharpe 1.8 (Oct 2011 - Oct 2012).
- **High frequency**: buy/sell volume imbalance predicts short-term moves; tactics (queue joining, quote stuffing, stop hunting, order flow); HFT profits come from slower traders and quoted sizes have shrunk.

## 7. [Adaptation] Perpetuals
- 24/7 markets have no overnight gap, so the book's "opening gap" and "overnight news" setups do not map directly; analogues are session opens, funding-time spikes, and liquidation cascades — **state them as hypotheses and test**, do not assume.
- Perps trend strongly but also gap through stops in liquidation cascades: model stop slippage with real worst-case moves.
- Use the book's test (non-overlapping lookback x holding grid, shortest holding) on our candles; keep the grid small and count it as trials.
- Funding is a persistent cost for the crowded side in trends: net it in every trend backtest.
- Expect crashes in regime flips; size with `chan-kelly-sizing` / `chan2-leverage-risk`, and validate with `chan2-backtest-significance`.
