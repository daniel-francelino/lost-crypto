---
name: chan-strategy-screening
description: Quick pre-backtest screen for a candidate trading strategy or idea, based on Ernest Chan's "Quantitative Trading" ch. 2. Use before spending time on a backtest of any new bot strategy, when someone proposes a strategy from a blog/paper/forum, or when asked "is this idea worth testing?" for Binance USDT-M futures bots.
---

# Strategy screening (Chan, *Quantitative Trading*, ch. 2)

Cheap checks that kill bad ideas **before** the backtest. Page numbers are book pages. Items marked **[Adaptation]** are ours for crypto perpetuals, not from the book (the book never discusses crypto).

Full chapter analysis vs. our code: `docs/books/01-quantitative-trading-chan/ch02-fishing-for-ideas.md`.

## 1. Does it fit the operator? (pp. 12-17)
Working hours, programming skill, capital, goal (steady income vs long-term growth). Shorter holding period = more regular income (p. 17). Here: bots run unattended, so require full automation and alerts on failure.

## 2. The six quick checks (pp. 18-27)
Run every one; record pass/fail/unknown. Unknown counts as a warning, not a pass.

| # | Check | Rule from the book |
|---|---|---|
| 1 | Benchmark and consistency | Long-short/neutral: compare with the risk-free rate; directional: with its market. Prefer Sharpe/information ratio over raw return (pp. 18-19). |
| 2 | Sharpe ratio | Sharpe < 1 is not fit as a stand-alone strategy; profitable almost every month => Sharpe usually > 2; almost every day => usually > 3 (p. 21). Few trades per year => Sharpe unlikely to be high (p. 20). |
| 3 | Drawdown depth and duration | Deep (> 10%) or long (>= 4 months) drawdowns => unlikely to have a high Sharpe (p. 20). Compare with the drawdown you can actually tolerate (p. 22). Max drawdown and max drawdown duration usually do not overlap (p. 21). |
| 4 | Transaction costs | Count spread/half-spread, commission, market impact and slippage (pp. 22-23). Example: a Bollinger-band mean-reversion on ES went from a very high Sharpe before costs to unprofitable after just 1 bp (p. 23). If the source does not say costs were included, assume they were not. |
| 5 | Survivorship bias | Was the data point-in-time? Be skeptical otherwise (p. 24). |
| 6 | Performance by year | Edges decay and regimes shift; judge mainly the **most recent** years, not the whole-sample number (pp. 24-25). Financial series are nonstationary, so more data is not automatically better (p. 25). |

Additional gates:
- **Data-snooping** (pp. 25-26): many rules/parameters => likely fitted to accidents. Simple models survive. Chan accepts ML only when it has a sound rationale, few parameters, linear form, conceptual simplicity, and all optimization inside a lookback window that is continuously checked on unseen data (p. 27).
- **Niche / capacity** (p. 27): for a small account, low-capacity strategies are an advantage because big funds cannot arbitrage them away.
- **Variations** (pp. 10-11): a published idea often fails as stated but can be made profitable by modifying it (holding period, entry/exit times). The variation is the proprietary part.

## 3. [Adaptation] Crypto perpetual futures
- Replace "survivorship bias" with **listing/delisting bias**: only currently listed USDT-M symbols in the sample inflate results. Use symbols as they existed at each date.
- Replace "benchmark" with: long-only vs holding the perp or spot; neutral vs funding-free cash. Funding is a financing-like cost/income and must be in the numbers.
- Costs = taker/maker fee + spread + slippage + funding. Use the real fee tier.
- "Recent years" matters more: crypto microstructure and fees changed fast. Weight the last 6-12 months.
- Capital is small (max 1000 USDT in this project): capacity is not a constraint, but min-notional and fees per order are.

## 4. Output
Write a short verdict: each check with pass / fail / unknown, the single biggest risk, and a decision: **drop**, **test with variations**, or **backtest as is**. Do not claim profitability; historical figures from sources are examples, not evidence of future returns.

Next step if it passes: `chan-backtest-hygiene`, then `quant-research` and `trading-strategy-review`.
