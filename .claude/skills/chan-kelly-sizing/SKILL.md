---
name: chan-kelly-sizing
description: Position sizing, leverage and risk-management rules from Ernest Chan's "Quantitative Trading" ch. 6 — Kelly formula, half-Kelly, worst-historical-loss cap, multi-strategy allocation, why stop-losses are not always good risk management, model/software risk. Use when deciding bot leverage, position size, capital split across strategies, or de-risking rules for Binance USDT-M perpetuals.
---

# Kelly sizing and risk (Chan, *Quantitative Trading*, ch. 6)

Page numbers are book pages. **[Adaptation]** marks crypto-specific additions that are ours, not the book's. Chapter analysis vs. our code: `docs/books/01-quantitative-trading-chan/ch06-money-and-risk-management.md`.

## 1. Objective (pp. 95-96)
Maximize long-term compounded growth `g`; this implies **ruin must be avoided** (if ruin has nonzero probability, long-term growth is zero). Returns are assumed Gaussian with fixed mean and std, net of financing costs — an approximation that is inaccurate in the tails.

## 2. Kelly formula (pp. 96-100)
- One strategy (or independent strategies): `f = m / s^2` (mean excess return over variance, same period units). `f` is independent of time scale.
- Several correlated strategies: `F = C^-1 M` (covariance matrix inverse times mean-return vector).
- Max growth: `g = r + S^2 / 2` (S = Sharpe) for one strategy; `g = r + F'CF / 2` for several. A higher Sharpe allows more leverage and more growth — this is why Sharpe, not raw return, is the number to maximize (p. 19, p. 98).
- Risk always lowers growth: for a zero-mean geometric random walk the compounded rate is `m - s^2/2 < 0` (Example 6.1, pp. 97-98).

## 3. Use it conservatively (pp. 98-107)
1. **Half-Kelly**: because inputs are estimated and returns are not Gaussian, cut the recommended leverage in half (p. 98).
2. **Leverage cap**: if the account has a max leverage `l`, scale each `f_i` by `l / sum|f_i|` (p. 98).
3. **Worst-loss cap**: take the largest historical one-period loss (period = your rebalancing period) and divide your maximum tolerable one-period equity drawdown by it. **Use the smaller of half-Kelly and this cap** (p. 105). Chan's example: with a 20% max tolerable day and a 20.47% worst day, max leverage ~1 vs half-Kelly 1.26, so even half-Kelly was not safe (pp. 105-106). The truly dangerous scenario is the one not yet in history (p. 106).
4. **Rebalance with equity**: Kelly reduces size after losses and increases it after profits; update at least daily. Re-estimate mean/std from a trailing window; for ~1-day holds Chan suggests ~6 months (pp. 102-103). A short lookback also lets exposure to a decaying strategy shrink gradually toward zero (pp. 103, 107).
5. When signal counts vary day to day, use Kelly to bound the **maximum** positions/capital; staying below Kelly is always safer (p. 103).

## 4. Stop-losses (pp. 106-107)
Stops do not protect against catastrophic gaps (fills come at much worse prices). A stop helps only if you believe you are in a **momentum** regime; if the market mean-reverts within the trade's life, a stop realizes losses that would have been recouped. News/fundamental moves tend to be momentum; moves with no news are often liquidity events that revert. Detail on exits: `chan-mean-reversion-momentum`.

## 5. Other risks (pp. 107-108)
- **Model risk** (bias/errors in the backtest, competition, structural change): have someone replicate the backtest independently; lower leverage gradually as the model loses (Kelly on trailing stats does this), rather than an abrupt shutdown after a large drawdown.
- **Software risk**: compare automated-system trades with the backtest's theoretical trades (see `chan-live-vs-backtest`).
- **Operational disasters** (connection, power): infrastructure redundancy.
- **Behavioral**: humans override systems after abnormal P&L; loss aversion makes traders hold losers and cut winners (pp. 108-109).

## 6. [Adaptation] Perpetual futures
- Exchange leverage is a **ceiling**, not a target. Position size should come from risk, and leverage is the output (never the input).
- Liquidation price must sit well beyond the stop; funding and fees belong in `m` (net returns).
- With max 1000 USDT, cap risk per trade and per day explicitly; the worst-loss rule should use 1-minute/hourly gaps seen on the traded symbols (including flash wicks), not only daily closes.
- Correlated symbols (BTC/ETH/alts) move together in stress: use the full covariance, not independence, when sizing several bots, and compute caps on the worst *joint* loss.
- Treat Kelly output as **advice for a human to confirm**, not an auto-order input, until it is validated out of sample.

## Worked formula (copy into code reviews)
```
f_full   = mean_excess / variance            # same period units
f_half   = 0.5 * f_full
f_tail   = max_tolerable_period_dd / worst_historical_period_loss
leverage = min(f_half, f_tail, exchange_cap, strategy_cap)
```
Report all four, and which one binds. This is a risk-sizing aid, not a profit forecast.
