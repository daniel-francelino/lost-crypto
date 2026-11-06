---
name: chan-mean-reversion-momentum
description: Strategy-type and exit-design rules from Ernest Chan's "Quantitative Trading" ch. 7 — mean reversion vs momentum, why mean-reversion backtests get inflated by bad quotes, half-life via Ornstein-Uhlenbeck, exit strategies, when stops help or hurt, stationarity/cointegration, regime caveats. Use when designing a bot's entry/exit logic, choosing between trend-following and mean-reversion, or setting holding periods.
---

# Mean reversion, momentum and exits (Chan, *Quantitative Trading*, ch. 7)

Page numbers are book pages. **[Adaptation]** marks crypto-specific additions that are ours, not the book's (the chapter's examples are equity pairs, ETFs and commodity futures with short selling). Chapter analysis vs. our code: `docs/books/01-quantitative-trading-chan/ch07-special-topics.md`.

## 1. Two kinds of edge (pp. 116-119)
Prices are either mean-reverting or trending (or random). Both can hold at different horizons. Chan finds general theories of either not very useful and says it is usually safe to assume mean reversion unless expected profits changed (his opinion).
- **Mean-reversion backtests are inflated by bad quotes**: a fictitious low quote is "bought", the next correct quote is sold at a profit. **Clean the data first** (p. 117).
- **Momentum sources**: slow information diffusion, incremental execution of a large order, herding. The last two have unpredictable horizons (pp. 117-119).
- **Competition**: mean-reversion edge shrinks toward zero; the momentum horizon shortens (a week-long hold may become a day, then unprofitable) (pp. 119, 140).

## 2. Stationarity and cointegration (pp. 126-133)
A stationary series is a mean-reversion candidate; two non-stationary prices can combine into a stationary spread (hedge ratio by regression; test with the cointegrating ADF). **Cointegration is not correlation** (KO/PEP correlation 0.4849 but not cointegrated). Stationarity pays only while it persists. Examples need short selling.
**[Adaptation]** Candidates in perps: a perp vs its spot/other-expiry, or related pairs; these spreads can break on delistings, funding shifts, and exchange events — re-test on a rolling window.

## 3. Regime shifts (pp. 119-126)
Regimes: bull/bear, volatility, mean-reverting/trending. Hidden Markov models assume constant transition probabilities and Chan finds them generally useless for trading; "turning-point" models are data-mining. Example 7.1 (perceptron on one stock: 37.93% gross over **six months**, 89 trades vs 15.77% buy-and-hold) is a short, not fully out-of-sample demonstration by the author's own note — do not treat it as evidence.

## 4. Exits (pp. 140-143)
Options: fixed holding period, target price, last entry signal, stop price.
- **Mean reversion**: estimate the holding period robustly with the **Ornstein-Uhlenbeck** model — regress `dz` on `z` (book model: `dz(t) = -theta * (z(t) - mu) * dt + dW`, with `mu` the mean and `dW` Gaussian noise; use the whole spread series, not only the days a trade was triggered, p. 141); **half-life = ln(2) / theta** (GLD/GDX ≈ 10 days, Example 7.5). Exit at the mean or after about one half-life; target price + half-life can serve as exit signals.
- **Momentum**: a holding period taken from few trades is error-prone.
- **Exit on a new opposite entry signal** acts as a stop with no extra parameter.
- A mean-reversion model **should not use a stop-loss** (it exits at the worst moment) unless it enters a momentum regime (see `chan-kelly-sizing` §4).

## 5. Seasonality, factors, high frequency (pp. 133-139, 143-153)
- Calendar effects in stocks weakened (January effect and year-over-year tests failed, Examples 7.6-7.7); commodity-futures seasonality persisted because of real demand but occurs once a year, so snooping is hard to rule out — vary dates and require economic logic.
- Factor models (`R = Xb + u`, Fama-French, PCA) work only if factor returns have momentum; the author's PCA strategy on small caps lost money.
- High frequency: more bets per day => higher Sharpe => more leverage; risk is easier to manage; needs bid/ask/book data, careful cost model, fast execution, and often only live testing is conclusive.
- High leverage vs high beta: growth depends on Sharpe^2, so prefer a low-beta book levered up (caveat: Gaussian assumption, fat tails) (pp. 153-154).

## 6. [Adaptation] Using this in the bots
1. Tag each strategy as trend or mean-reversion **before** testing, and give its exit accordingly (trend: stop/trailing is coherent; reversion: half-life or target, no price stop beyond a hard liquidation guard).
2. Compute the half-life from the instrument's own recent data; re-estimate on a rolling window and compare with the configured max-hold. Treat the estimate as noisy.
3. Run data cleansing (bad ticks, gaps) before any reversion backtest.
4. For perps, funding is a drag/credit that scales with holding time: a longer hold implied by the half-life must net funding.
5. Validate with `chan-backtest-hygiene` before trusting any result; none of the book's historical numbers is evidence of future returns.
