---
name: chan2-backtest-significance
description: Backtest validity and statistical-significance rules from Ernest Chan's "Algorithmic Trading: Winning Strategies and Their Rationale" ch. 1 — look-ahead and data-snooping bias, walk-forward as the final test, the "live Sharpe above half of backtest" expectation, hypothesis testing of backtest returns (normal, Monte Carlo, random entry dates), red flags for when not to backtest, and regime-change limits. Use when judging whether a bot backtest result is real or luck, or setting the acceptance test before going live.
---

# Backtest validity and significance (Chan, *Algorithmic Trading*, ch. 1)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (it never treats crypto). Chapter analysis vs. our code: `docs/books/02-algorithmic-trading-chan/ch01-backtesting-and-automated-execution.md`. Complements `chan-backtest-hygiene` (book 1 mechanics).

## 1. Principles (pp. 1-7)
- Backtest every strategy yourself; results depend on implementation details (order type, trigger price). Use **the same program** for backtest and live: it removes transcription errors and look-ahead (p. 4). A published strategy gives a genuine out-of-sample window **after publication**.
- **Data-snooping**: too many free parameters. Detect with out-of-sample data; adjusting after a bad out-of-sample result turns it into training data. Use **cross-validation**; high Sharpe and short maximum drawdown duration tend to survive it. Use few parameters **and few rules**; **linear models are less prone to snooping than nonlinear ones** (if nonlinear, justify why the linear approximation fails). Equal-weighted factor combinations (z-scores or signed ranks) are a robust example (pp. 4-7).
- **Walk-forward test is the final check**: paper trading, or better, real money at minimal leverage. **Most traders would be happy if live Sharpe is better than half of the backtest Sharpe** (p. 7, author's experience).

## 2. Is the result luck? Hypothesis test on returns (pp. 15-22)
Null hypothesis: true mean return is zero. Test statistic = mean daily return. Three ways to build the null distribution — they can disagree because each defines randomness differently:
1. **Normality**: `t = mean / std * sqrt(n)` (= daily Sharpe x sqrt(n)). Critical values 1.282 / 1.645 / 2.326 / 3.091 for p = 0.10 / 0.05 / 0.01 / 0.001.
2. **Monte Carlo** on simulated prices preserving the first four moments of the real series (book example: 1,166 of 10,000 simulations did as well or better => only 88% confidence).
3. **Random entry dates** keeping number of trades and holding period (Lo et al.; book example: 0 of 100,000 did as well).
Caveats: a p-value is P(result | H0), not P(H0 | result). More completed round-trip trades => more significance.
**[Adaptation]** Report all three; if they disagree, say so and trust the most conservative. Count the number of variants tried (trial count) next to the p-value.

## 3. When NOT to backtest (pp. 22-24)
Skip ideas that show these red flags: high return with Sharpe ~0.3 and a two-year drawdown; a long-only strategy that does not beat buy-and-hold on the information ratio; "buy the cheapest stocks" without survivorship-free data; neural nets with ~100 nodes; high-frequency results that depend on how other participants react.

## 4. Does a backtest predict the future? (pp. 24-25)
It assumes constant statistical properties; regime changes (decimalization 2001, 2008 crisis, Reg NMS 2007, uptick rule changes) can make older data useless — and recent data is no guarantee either. **[Adaptation]** For crypto: fee-tier changes, funding mechanics, listing waves, and market-structure events (2020-21 cycle, exchange collapses) are regime breaks; split results by period.

## 5. Data traps (pp. 7-16) — pointers
Splits/dividends adjustment; survivorship (hurts long mean reversion more than momentum); primary vs consolidated prices (consolidated highs/lows are exaggerated and inflate mean-reversion results); exchange-dependent FX quotes (use the venue you trade); short-sale limits; continuous futures roll gaps (backward adjustment by price vs by return cannot both be right; negative prices); settlement vs last price; asynchronous prices in spreads.
**[Adaptation]** Use Binance's own mark/index/last convention consistently; funding timestamps; no contract roll for perpetuals but delivery contracts do roll.

## Acceptance template (before going live)
```
Hypothesis: <mechanism, who is on the other side>        Falsifier: <result that kills it>
Parameters: <n, <= 5>   Rules: <n>   Trials tried: <N>
In-sample / out-of-sample split: <dates, frozen>
Cross-validation: <result>        Walk-forward / paper: <period, Sharpe vs backtest>
p-values: normal <..>  Monte Carlo <..>  random entry <..>
Live expectation: Sharpe >= 0.5 x backtest Sharpe, else investigate (see chan-live-vs-backtest)
```
No historical result here is a promise of future returns.
