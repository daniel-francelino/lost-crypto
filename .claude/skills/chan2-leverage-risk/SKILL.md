---
name: chan2-leverage-risk
description: Leverage and risk-control rules from Ernest Chan's "Algorithmic Trading" ch. 8 — constant leverage, Kelly as an upper bound and half-Kelly, multi-strategy allocation under a leverage cap, Monte Carlo growth optimization with Pearson-fitted returns, maximum-drawdown constraint, CPPI, when stop-losses help or hurt (mean reversion vs momentum), leading risk indicators. Use when setting bot leverage, a drawdown budget, a kill-switch/de-risking policy, or a stop-loss policy for Binance USDT-M perpetual bots.
---

# Leverage, drawdown and stops (Chan, *Algorithmic Trading*, ch. 8)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book. Chapter analysis vs. our code: `docs/books/02-algorithmic-trading-chan/ch08-risk-management.md`. Builds on `chan-kelly-sizing` (book 1).

## 1. Framing (pp. 169-170)
Goal: maximize long-term wealth growth; avoid risk only where it hurts that goal. Loss aversion (~$2 of gain per $1 of loss, Kahneman) explains why Sharpe 2 feels good but is not itself rational.

## 2. Optimal leverage assumptions (pp. 170-171)
Future returns distributed like past ones (stricter: the strategy's own distribution does not change; strictest: Gaussian); no ruin in history; a max-drawdown limit is an extra constraint. **Leverage must stay constant**, so you sell after losses and buy after gains (Example 8.1: leverage 5, equity 100k -> 90k forces selling down to 450k). Selling after losses was blamed for contagion in the August 2007 quant crisis.

## 3. Kelly as an upper bound (pp. 172-175)
- `f = m / sigma^2`. Overestimating the mean or underestimating variance overestimates leverage and can ruin; underestimating them only slows growth => **use half-Kelly**.
- In the author's experience **Kelly is an upper bound**: Kelly computed from a backtest often exceeds broker limits or would have ruined the account because returns are not Gaussian (Russell 1000/2000 Kelly ~1.8 vs 3x ETFs).
- Several strategies: `F = C^-1 M`. Under a maximum-leverage cap, scaling all equally is **not** optimal (Example 8.2, cap 2: all buying power on the best-growth strategy g = 0.96 vs 0.82 with proportional scaling).
- Compute Kelly **per strategy** so the worst can be eliminated quickly, rather than pooling (p. 188).

## 4. Monte Carlo growth optimization (pp. 175-178)
`g(f) = <log(1 + f*R)>` over simulated per-bar returns R drawn from a **Pearson-system** distribution matched to the strategy's mean, std, skewness and kurtosis; maximize numerically. Example: Kelly 18.4, Monte Carlo ~19, historical optimization 18.4; any leverage above `1/|worst return|` (30.2) leads to -100%. Direct optimization on historical returns suffers from snooping though it agreed here.

## 5. Maximum-drawdown constraint (pp. 179-180)
Drawdown does not scale linearly with leverage. Unconstrained optimum produced -99.9% simulated drawdown; half of it still -96.3%; leverage had to drop ~7x (to 2.7) to reach -50% (historical returns needed only 1.5x). Simulated returns add power but may lose autocorrelation and represent extreme rare events; historical returns capture correlation but are few => **combine both**. Leverage limits do not guarantee future drawdowns.

## 6. CPPI (pp. 180-182)
Let `f` be the Kelly leverage and `D` the maximum drawdown you accept. Put **D of equity** in a trading subaccount, apply leverage `f` to it, keep `1 - D` in cash. **Replenish the subaccount to D of total equity only on a new all-time high; never after losses.** If it is exhausted, retire the strategy — a principled wind-down instead of an emotional one. The author's simulation: growth ~ equal to the equivalent fixed leverage (0.002484 vs 0.002525 per day) but drawdown capped near D (0.5 vs 0.9). One strategy per account; it does not protect against gaps or trading halts and is **not** the same as applying leverage `f*D` to the whole account.

## 7. Stop-loss policy (pp. 182-184, 108)
- Per-position vs per-strategy (the latter is awkward and used once; the author prefers CPPI). A stop works only while the market is open and liquid; it can fail when liquidity vanishes (2010 flash crash: an Accenture stop filled at $0.01).
- **Mean reversion**: stops lower backtest performance, partly because of **survivorship bias** (strategies whose regime turned to trend never entered the catalogue). Place the stop **beyond the largest intraday drawdown of the backtest**, so it never triggers in the backtest and exists only for black swans.
- **Momentum**: the opposite signal is already the stop, which limits tail risk.
- Currencies/24h markets: stops make sense because there are no long closing gaps (p. 108).

## 8. Leading risk indicators (pp. 184-186)
VIX, TED spread, HYG, MXN, order flow, etc. can steer you away from risky periods but are strategy-specific: VIX > 35 *helped* buy-on-gap and *hurt* the FSTX gap strategy (Sharpe 1.4 -> 0.16). Crises are rare, so selecting data on these indicators is easy to overfit.

## 9. Judgment calls (pp. 187-189)
Reducing leverage before a known event: the author says no if the model already survived earlier stress; start conservative. Live vs backtest gaps are often **regime change**, not backtest flaws. Hypothesis -> model -> test on unseen data.

## 10. [Adaptation] Bot policy sketch for perpetuals (to be reviewed, not auto-applied)
1. `leverage = min(half-Kelly, worst-loss cap [from chan-kelly-sizing], exchange cap, strategy cap)`; with max 1000 USDT, also fix a hard USDT risk per trade/day.
2. One strategy per account/sub-account where possible; a per-strategy CPPI subaccount of size D with replenishment only on new equity highs; exhausted => bot retired and flagged for review.
3. Constant-leverage rebalance rule defined explicitly (how often, tolerance), with fees counted.
4. Liquidation price must be far beyond any strategy stop; for reversion bots the stop sits beyond the worst backtest adverse excursion and is an emergency exit only.
5. Risk indicators (funding extremes, open-interest spikes, volatility regime) may pause entries only after being tested per strategy out of sample.
6. Per-strategy Kelly/Sharpe tracking so a decaying bot is shrunk automatically toward zero.
No historical figure in the book is a forecast of returns.
