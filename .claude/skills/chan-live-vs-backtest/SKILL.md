---
name: chan-live-vs-backtest
description: Execution-system and paper-trading rules from Ernest Chan's "Quantitative Trading" ch. 5 — automate faithfully, minimize transaction costs, cap order size at ~1% of volume, use paper trading to compare against the backtest, and a diagnosis order for why live results diverge. Use when building or reviewing bot execution, paper trading, order sizing, or when live/paper performance is worse than the backtest.
---

# Execution and live-vs-backtest (Chan, *Quantitative Trading*, ch. 5)

Page numbers are book pages. **[Adaptation]** marks crypto-specific additions that are ours, not the book's (the book's broker tooling — DDE links, basket traders, MATLAB, TradeStation — does not apply). Chapter analysis vs. our code: `docs/books/01-quantitative-trading-chan/ch05-execution-systems.md`.

## 1. Automated system (pp. 79-85)
It fetches data, runs the algorithm and sends orders. Full automation minimizes human error and delay and is required for high frequency; semi-automation suits a few order waves per day. Often the same program generates the backtest and the live orders — keep one code path so they cannot drift.

## 2. Minimize transaction costs (pp. 87-88)
- **Cap each order at about 1% of average daily volume** (rule of thumb, p. 87).
- Scale position size sublinearly with market cap to keep diversification (book example: fourth root).
- Splitting big orders trades market impact for slippage; it does not help small traders.
- Broker risk/speed checks cause slippage outside your control.
- **[Adaptation]** For perps: volume cap uses the symbol's recent quote volume and book depth; include maker/taker choice, funding, and min-notional/step-size rounding as explicit cost items.

## 3. Paper trading (pp. 89-90)
The only way to find software bugs without losing money; also reveals look-ahead ("you could not have had that data"). **Compare the paper trades and P&L with the backtest run on the same recent data. Differences not explained by costs (including expected execution delay) mean bugs.** It also gives intuition for P&L volatility, capital used, trades per day, and operational timing. A month or more can reveal data-snooping, but attention to paper accounts fades, so snooping is usually revealed only by trading small real capital.

## 4. Why live diverges from backtest — diagnose in this order (pp. 90-94)
1. **Bugs** in the automated system.
2. **Trade parity**: do live trades match the backtest's trades on the same data?
3. **Execution costs** higher than assumed.
4. **Illiquidity / market impact.**
5. **Data-snooping**: remove rules and parameters; if the backtest collapses, snooping is likely; if it stays reasonable, bad luck is possible.
6. **Regime change** (book examples: decimalization in 2001, the uptick rule until 2007, hard-to-borrow stocks).
Bad luck can never be proven.

## 5. Practical checklist
- [ ] One strategy code path for backtest, paper and live.
- [ ] Each bot run records intended price, fill price, latency, fees, funding — so slippage is measured, not assumed.
- [ ] Daily diff: bot trades vs. backtest replay on the same candles; unexplained diffs open an issue before trading continues.
- [ ] Order size <= ~1% of volume proxy; rounding and min-notional handled.
- [ ] Paper phase length and exit criteria written down before starting.
- [ ] Live starts with a small capital step, comparing against paper.

Related: `chan-backtest-hygiene` (look-ahead, costs), `chan-kelly-sizing` (software/model risk).
