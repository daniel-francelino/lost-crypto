---
name: chan-backtest-hygiene
description: Backtest correctness checklist from Ernest Chan's "Quantitative Trading" ch. 3 — Sharpe annualization, drawdown calculation, look-ahead bias and the truncation test, data-snooping limits, out-of-sample and rolling optimization, sensitivity analysis, cost impact. Use when writing, running or reviewing any backtest or metric code for the bots, or when a backtest result looks too good.
---

# Backtest hygiene (Chan, *Quantitative Trading*, ch. 3)

Page numbers are book pages. **[Adaptation]** marks crypto-specific additions that are ours, not the book's. Chapter analysis vs. our code: `docs/books/01-quantitative-trading-chan/ch03-backtesting.md`.

## 1. Metrics (pp. 43-50)
- **Sharpe**: use excess returns. Do **not** subtract the risk-free rate for dollar-neutral or purely intraday strategies (no financing cost); subtract it when the strategy is financed (pp. 43-47).
- **Annualize**: `Sharpe_annual = sqrt(N_T) * Sharpe_period`, where `N_T` = number of periods per year *actually traded*. Book examples: daily `sqrt(252)`; hourly US session `N_T = 252 * 6.5 = 1638`. The book calls `252 * 24` for hourly a common mistake **for a session market**.
  - **[Adaptation]** Crypto trades 24/7, so by the same principle `N_T` is calendar periods: 365 daily, 365*24 hourly. State the convention in every report.
- **Drawdown** (Example 3.5, pp. 48-50): cumulative compounded return; running high watermark; `drawdown = (1 + HWM)/(1 + cum) - 1`; duration counter resets to 0 at a new high, else +1; report max drawdown **and** max drawdown duration.
- Prefer Sharpe + drawdown over headline annual return (denominator and leverage make raw return ambiguous).

## 2. Data (pp. 36-43)
- Adjust for corporate events so returns are not distorted. **[Adaptation]** For crypto: symbol renames, contract rollover/redenomination, listing gaps, exchange maintenance gaps.
- **Survivorship**: toy example flipped from -42% to +388% depending on delisted names (pp. 40-42). **[Adaptation]** Keep point-in-time symbol lists (delistings, delivery contracts).
- **High/low are noisier than open/close**: a limit order "below the low" may never have filled. Sanity check: inspect returns beyond ~4 standard deviations and require a news/market-wide explanation (pp. 42-43). Bad ticks inflate mean-reversion backtests (p. 117).

## 3. Look-ahead bias (pp. 51-52, 59)
Using information not available at decision time (e.g. the day's low, regression coefficients fitted on the whole sample). Fix by lagging signal inputs.
**Truncation test**: run on all data, save positions A; truncate the last N periods (10-100), rerun, save B; cut A to B's length; they must be **identical**.
**[Adaptation]** For candles, a signal computed on a bar can only trade at the *next* bar's open; a bar still forming is not usable.

## 4. Data-snooping limits (pp. 52-53)
- At most **5 free parameters** (rule of thumb); qualitative choices (enter at open vs close, hold overnight) count too.
- Sample size ~ **252 x number of free parameters**, counted in *independent* observations (7 months of minute bars for a daily model is only ~147 points). Chan states this is from experience, not literature.

## 5. Out-of-sample (pp. 53-55)
- Train first, test on the later part; test set at least one third of the training size, ideally about equal halves. If the test is poor, **simplify** the model.
- Rolling-window re-optimization is the most rigorous form; a "parameterless" model re-optimizes inside a moving lookback. Averaging across parameter sets beats picking one "best".
- Paper trading is the final out-of-sample test; time since publication counts only if you did not tune on it.
- Never tweak to improve the test set — it becomes training data.

## 6. Sensitivity (p. 60)
Vary parameters and make small qualitative changes. A model that works only at the exact optimum is overfit. Remove conditions one by one and keep removing while the **test** result does not worsen. Then split capital across parameter values.

## 7. Costs (pp. 60-65)
Example 3.7: Sharpe 4.47 before costs on small caps became 0.25 on the S&P 500 and -3.19 after 5 bp per trade. Treat results without survivorship-free data as **upper bounds**. Small refinements (e.g. acting at the open instead of the close, Example 3.8) can change the result a lot — keep only ones with economic logic that improve train **and** test (pp. 65-66).
**[Adaptation]** Cost = fee + spread + slippage + funding, applied per side; run the cost-ladder (0 / realistic / pessimistic) and show how the Sharpe moves.

## Review checklist
1. Annualization factor stated and correct for the bar size and 24/7 calendar.
2. Funding and fees included; cost ladder shown.
3. Truncation test passes.
4. Parameter count <= 5; observations >= 252 x parameters (independent).
5. Train/test split fixed in advance; test not used to tune.
6. Sensitivity grid shows a plateau, not a spike.
7. Outliers beyond ~4 sigma explained.
8. Result reported with drawdown depth and duration.

Escalate to `quant-research` (deflated Sharpe, trial counting) and `trading-strategy-review` for the severity-rated audit. No result here guarantees future returns.
