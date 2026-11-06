---
name: chan2-mean-reversion-build
description: Building and operating mean-reversion strategies from Ernest Chan's "Algorithmic Trading" ch. 3-5 — spread vs log-spread vs ratio, Bollinger-band entry/exit with half-life lookback, why scaling-in is never optimal in-sample, Kalman filter for dynamic hedge ratio, data-error inflation, why stock pairs decay while ETF baskets are sturdier, buy-on-gap and cross-sectional reversion, futures roll returns and the carry/funding analogy. Use when implementing or reviewing a reversion/spread bot or deciding how to enter, add to and exit positions.
---

# Implementing mean reversion (Chan, *Algorithmic Trading*, ch. 3-5)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (its instruments are US ETFs, FX pairs and commodity/volatility futures). Chapter analyses: `docs/books/02-algorithmic-trading-chan/ch03-*.md`, `ch04-*.md`, `ch05-*.md`. Test first with `chan2-mean-reversion-tests`.

## 1. Choosing the signal series (ch. 3, pp. 63-70)
- True stationarity/cointegration is not required: short-term or seasonal reversion can be traded if you exit before the next equilibrium shift (p. 63).
- **Price spread** `y = sum(h_i * y_i)` fixes the quantity of units; a **log-price combination** fixes capital weights and needs constant rebalancing (extra cost); a **ratio** is stationary only if hedge ratios have equal magnitude but can work better for non-cointegrated pairs and avoids a dynamic hedge ratio. FX pairs are ratios by nature. Book example GLD/USO: price spread with dynamic hedge ratio beat log-spread and ratio (10.9% / Sharpe 0.59 vs 9% / 0.5 vs negative), without costs.

## 2. Bollinger-band strategy (pp. 70-72)
Enter when the spread z-score exceeds `entryZscore` (below -entry => long); exit at `exitZscore` (< entry; 0 = mean; -entry = opposite band). Lookback free or **set to the half-life**. Holding at most **one unit** simplifies capital and risk. GLD/USO: 17.8% / Sharpe 0.96 with entry 1, exit 0 (author's example, no costs).

## 3. Scaling in (pp. 72-74)
Adding at several bands feels intuitive, but **Schoenberg and Corwin show averaging-in is never optimal in-sample** when the probability of a further drop stays constant (a single entry/exit level always gives a higher average return). It can help out of sample when volatility (hence that probability) changes, and it can reduce market impact. Scaling **out** gradually can still pay if the series is not truly stationary. Default for the bots: a single entry per signal; justify scaling-in with a volatility-regime argument and test it separately.

## 4. Kalman filter regression (pp. 74-83)
Observed `y(t) = x(t)*beta(t) + eps`; hidden state `beta(t) = beta(t-1) + omega`. It yields, bar by bar, a **dynamic hedge ratio**, the **intercept** (replaces the moving average) and the forecast-error variance `Q(t)` (replaces moving std). Parameters (delta 0.0001, V_e 0.001 in the example) were picked "with hindsight". EWA/EWC example: 26.2% / Sharpe 2.4 without costs. Benefit: no abrupt fixed-window effects. Risk: its parameters are extra snooping surface. **[Adaptation]** Only adopt if it beats a rolling-regression baseline out of sample, with the delta/V_e frozen beforehand.

## 5. Data errors inflate reversion (pp. 83-84)
A wrong high tick is "sold" and "bought back" for fictitious profit — the opposite effect for momentum. Spreads amplify quote errors ($1 on a $5 spread = 20%). The author lost real money to a broker feed error that vanished after a provider change. **Clean ticks/candles before any reversion backtest** and validate live data against a second source.

## 6. Stocks/ETFs (ch. 4, pp. 87-106)
- Individual stocks are almost never stationary; **pairs cointegrated in one period often stop being so afterward** as the companies diverge. Trading many pairs only helps if the out-of-sample expectation per pair is positive (losses of bad pairs can exceed small gains of good ones).
- **ETF pairs/triplets are sturdier** because a basket's economic composition changes slowly. GLD/GDX cointegrated 2006 to July 2008 and not afterwards; adding USO restored it (2006-2012). Lesson (p. 92): when a strategy stops working, **form a hypothesis and test it empirically**.
- **Buy-on-gap** (pp. 92-96): select by overnight drop below -1 std **but with open above the 20-day average** (a momentum filter inside a reversion model: small drops revert, large ones may be news). 8.7% / Sharpe 1.5 (2006-2012, no costs, survivorship bias; weakens after 2009 without the filter). Series that do not revert on daily bars may revert in **specific periods**.
- **Cross-sectional reversion** (pp. 102-105): weights `w_i = -(r_i - mean r) / sum|r_k - mean r|`, gross exposure always 1, no parameters, near dollar-neutral. S&P 500 2007-2011: 13.7% / Sharpe 1.3; the open-to-close version doubles transaction costs and has signal noise. Profit appears only in the aggregate basket.

## 7. Currencies and futures (ch. 5, pp. 107-131) — what transfers
- Currencies and futures tend to favour momentum; reversion is the exception. 24h markets without long closing gaps make **stops meaningful** (p. 108).
- **Excess return = return - financing cost**; zero financing for intraday, dollar-neutral stocks and futures. Ignoring the FX rollover (~5%/yr average in the AUD.CAD example) overstated the result (6.7% vs 6.2%, Sharpe 0.54) (pp. 113-115).
- **Futures return = spot return + roll return** (backwardation positive roll; contango negative). For corn the roll (-12.8%) dwarfed the spot return (2.8%); VX sits in contango ~75% of the time with an average roll near -50%/yr (pp. 115-122). Reversion in the spot does not imply reversion in the future.
- Spreads between different markets rarely revert (structural reasons) (pp. 127-129). Relationships can have **two regimes** (VX vs ES): fit only one regime, never mix them (pp. 129-131).
- **[Adaptation]** The perpetual's equivalent of roll return/financing is **funding**: include it as a cost/credit per 8h interval in every spread or basis backtest; delivery contracts add a real roll.

## Checklist
1. Series type chosen deliberately (spread / log / ratio) and justified.
2. Lookback tied to half-life; hedge ratio from training data only.
3. Single entry per signal unless scaling-in is justified by volatility regimes.
4. Data cleaned; second-source check.
5. Funding/financing and fees in net returns.
6. Out-of-sample stability of the relationship demonstrated (rolling re-test).
7. Exit policy consistent with the thesis (see `chan2-leverage-risk` §stops).
