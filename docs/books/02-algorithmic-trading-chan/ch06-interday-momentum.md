# Book 2 · Chapter 6 — Interday Momentum Strategies

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 133–154 was read.

This is the chapter closest to what Lost Crypto runs today (trend/breakout, long-only). Its examples are futures, stocks and news-sentiment portfolios; results exclude costs (book 2 ch. 3 caveat) and use pre-2013 data.

## 1. Chapter summary (pp. 133–154)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Four causes of momentum: persistence of futures roll-return signs; slow diffusion/acceptance of information; forced sales/purchases by funds; manipulation by high-frequency traders. *Time-series* momentum (own past return correlates with future return) vs *cross-sectional* (relative performance persists). | Understanding why trends exist. | 133–134 |
| C2 | **Testing time-series momentum**: correlation (and p-value) between the return over a look-back window and the return over a following holding window, for a grid of (look-back, holding) pairs, **using non-overlapping pairs** (shift by the longer window); also correlation of *signs*; Hurst exponent and variance ratio as global tests. TU futures: best compromises between correlation and p-value at (60,10), (60,25), (250,10), (250,25), (250,60), (250,120); H = 0.44 and the variance ratio test did not reject a random walk, because momentum and reversion coexist at different horizons. Prefer the shortest holding period (better Sharpe). | Choosing look-back and holding period with evidence. | 134–137 |
| C3 | **Time-series strategy** (Moskowitz et al.): long if the 12-month return is positive, short if negative, hold 1 month; made daily by investing 1/25 of capital each day (staggered tranches). TU: Sharpe ≈ 1, APR 1.7% on notional, max drawdown 2.5%. BR, HG and TU also work (Table 6.2). Explanation for futures: the sign of the roll return persists. A **lagged roll-return signal** (threshold 3%) did better (Sharpe 2.1). Few trades, so **data-snooping risk is real**; true out-of-sample is the test. | A baseline momentum rule. | 137–141 |
| C4 | Other entry signals: new N-day high, price above an (exponential) moving average, upper Bollinger band, more up days than down days in a window, the Alexander filter (x% up-move entry, x% retracement from a high exit). **Combining reversal and momentum rules** can work better (CL: buy if price is below its level 30 days ago but above its level 40 days ago; APR 12%, Sharpe 1.1). The S&P Diversified Trends Indicator (above-EMA long, below short): Sharpe 1.3, max drawdown −16.6% (1988–2010) but poor since 2008. | Entry rule menu and combinations. | 140–141 |
| C5 | Roll-return extraction through futures/ETF arbitrage, VX vs ES (APR 6.9%, Sharpe 1) and cross-sectional futures momentum (rank 12-month returns; APR 18%, Sharpe 1.37 in 2005–2007, then −33% APR in 2008–2009). Cross-sectional stock momentum (top vs bottom decile of 12-month return, held 25 days): Sharpe 4.1 in 2007, then −30% APR in 2008–09; Daniel & Moskowitz long run: 16.7% return, Sharpe 0.83 (1947–2007). Factor view: stock return = market return + factor returns. | Cross-sectional alternatives. | 141–148 |
| C6 | **News sentiment** as a factor (Hafez & Xie: APR 52–156%, Sharpe 3.9–5.3 before costs); Twitter mood research is questioned. **Mutual-fund forced sales/purchases** (Coval & Stafford): a PRESSURE factor from holdings and flows; about 17% + 17% + 7% before costs; data costs about $10,000/year and delays cause slippage. | Event/flow-driven momentum. | 148–151 |
| C7 | **Cons of momentum**: harder to make profitable; usually lower Sharpe because look-backs and holds are long, so there are **few independent signals**; **momentum crashes** after financial crises (Daniel & Moskowitz; after 1929 a momentum strategy needed more than 30 years to regain its high); the duration of news-driven momentum **shrinks as more traders arrive**, with no schedule to adjust the holding period. | Realistic expectations. | 151–153 |
| C8 | **Pros**: stop-losses are consistent with momentum (an opposite entry signal is effectively a stop); exits are time-based or stop-based, so **loss per position is limited and upside is unlimited**; heavy tails (high kurtosis) favour momentum (in Example 1.1, a random series with TU's kurtosis and no autocorrelation matched TU's momentum return in 12% of draws); diversification across asset classes; combining momentum with mean-reverting strategies lifts Sharpe and lowers drawdown. | Why still use it. | 153–154 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Time-series momentum strategies | ✅ | `ema_crossover` (above-EMA logic), `donchian_breakout` (new N-day high) already cover two of the entry families in C4. |
| Opposite signal as stop | ✅ | Both strategies exit on the opposite signal; optional `stop_loss_pct` and `take_profit_pct` exist; stop fills with the gap-through-open rule. |
| Time-based exit | ❌ | No `max_holding_candles` (also noted in book 1 ch. 7 O2). |
| Look-back/hold chosen by evidence | ❌ | Parameters come from the operator and from sweeps; no correlation grid or momentum test. |
| Staggered tranches (1/N capital per day) | ❌ | One position per bot; no tranche concept. Start-date luck is not measured. |
| Combined momentum + reversal rules | ❌ | Not in the catalogue. |
| Cross-sectional momentum | ❌ | Single asset per bot. |
| News sentiment / flow factors | ❌ | No external data. |
| Few independent signals warning | ⚠️ | `round_trips` is reported but nothing warns about a low count (book 1 ch. 3 O6, book 2 ch. 1 O3). |
| Momentum-crash / regime awareness | ❌ | None (book 2 ch. 5 O1 proposes named breaks). |
| Costs | ✅ | Always included in backtests. |

## 3. Opportunities

### O1 — Lag-correlation momentum diagnostics *(book: C2, pp. 134–137)*
* **Problem:** the look-back/holding period of trend strategies is chosen by sweeping, which maximises snooping; the book gives a statistically grounded way to *find where momentum exists*.
* **Proposal:** extend the series-diagnostics module (book 2 ch. 2 O1) with a grid of non-overlapping `(look-back, holding)` return pairs → Pearson correlation and p-value (and the sign-based version), displayed as a table/heatmap in the market-data page with sample counts. Show Hurst/variance ratio next to it and explain that they can disagree.
* **Benefit:** evidence-based starting ranges for `fast/slow_period`, `entry/exit_period` and a holding limit; far more power than counting backtest trades (the point made in book 2 ch. 2).
* **Complexity:** low–medium (pure functions; needs p-values for a correlation, i.e. a t-distribution survival function, to be implemented or approximated deliberately).
* **Risks:** the grid itself is a multiple-testing problem (49 pairs in the book's example); crypto returns are fat-tailed and volatility-clustered; non-overlapping samples are few at long horizons (the book's own p-values are borderline: 0.017–0.09); correlation is not tradable profit.
* **Validation:** synthetic AR(1) series with known positive/negative autocorrelation; random walk should show insignificant correlations; counts match the non-overlap rule.

### O2 — Time-based exit option *(book: C3, C8, pp. 137–138, 153)*
Already proposed in book 1 ch. 7 O2. This chapter adds the evidence-based way to choose it (O1) and the point that time exits plus stops give a **bounded loss per position**. Add as an optional parameter on both strategies and keep it out of default sweeps. **Complexity:** low.

### O3 — Start-date sensitivity (a cheap substitute for staggered tranches) *(book: C3, p. 138 · adaptation)*
* **Problem:** a single run begins on one date; results can depend on that date, especially with few trades. The book removes this by investing 1/25 of capital every day, i.e. 25 overlapping tranches.
* **Proposal:** re-run the same configuration with several start offsets (for example shifting the start by 0..N candles or days) and report the dispersion of return/drawdown. It needs no change to the one-position-per-bot model.
* **Benefit:** a direct measure of how fragile a result is to timing; it works for any strategy. **Complexity:** low–medium (compute cost; run batching exists through sweeps). **Risks:** shifting the start changes warm-up and the first trade; interpret as dispersion, not an expected value. **Validation:** a strategy with a deliberate timing artefact must show wide dispersion.
* The real staggered-tranche portfolio is recorded as **B-TRANCHES** (needs several concurrent sub-positions per bot).

### O4 — Warn on few independent signals and long-horizon strategies *(book: C7, p. 151)*
Add to the red-flags block (book 2 ch. 1 O3): number of round trips below a threshold relative to the number of free parameters; holding period large relative to the sample length. Thresholds configurable. **Complexity:** low.

### O5 — Research a momentum + reversal combination *(book: C4, p. 140 · hypothesis only)*
* The book reports, for one futures contract, that adding a "price lower than 30 days ago but higher than 40 days ago" structure beat each rule alone. There is no evidence for crypto. Treat as an **experiment**: a strategy variant whose entry uses a longer-term trend condition and a shorter-term pullback condition (a common construction), evaluated only after the integrity, truncation and cost-sensitivity work. Hypothesis ID **H-MOM-REV**. **Complexity:** medium; high snooping risk (more rules, more parameters).

### O6 — Momentum-crash awareness *(book: C7, pp. 151–153; ties to book 2 ch. 5 O1)*
Use named regime breaks and per-regime metrics to see whether the strategy's performance collapsed after market-wide crashes, and show it prominently. For the live side, the existing drawdown and daily-loss pauses are the protection; no new mechanism proposed. **Complexity:** depends on book 2 ch. 5 O1.

### O7 — Cross-sectional momentum across a coin basket *(book: C5, pp. 144–148)*
Research-only report (rank the stored pairs by trailing return and test whether the top bucket continues), long-only. Same limitations and backlog id as book 2 ch. 4 O4 (**B-MULTI-ASSET**). Survivorship bias is acute for coins that were delisted.

### Not applicable
Roll-return signals and futures/ETF arbitrage, VX–ES, news sentiment feeds, mutual-fund pressure factors.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O4 few-signals warning | medium | – | – | low | book 2 ch. 1 O3 |
| 2 | O1 momentum diagnostics | high | – | – | low–medium | book 2 ch. 2 O1 |
| 3 | O3 start-date sensitivity | high | – | – | low–medium | sweep infrastructure (exists) |
| 4 | O2 time-based exit | low | medium | – | low | O1 for choosing values |
| 5 | O6 crash awareness | medium | medium | – | low | book 2 ch. 5 O1 |
| 6 | O5 momentum + reversal experiment | medium | – | – | medium | integrity, truncation, cost sensitivity |
| 7 | O7 coin cross-section report | low | – | – | medium | multi-pair data |

## 5. Affected files
`analytics/domain/` (correlation grid, p-values), `market_data/presentation/router.py` (diagnostics endpoint), `strategies/domain/ema_crossover.py` and `donchian_breakout.py` (optional exit parameter) and `base.py`, `backtesting/application/service.py` (start-offset batches), `docs/openapi.json`, app market-data diagnostics panel and backtest form, `lib/shared/strategies/params.ts`, tests.

## 6. Incremental plan
1. Red-flag counts (cheap).
2. Diagnostics module: correlation grid and p-values with synthetic tests.
3. Start-date sensitivity runner on top of sweeps.
4. Optional time-based exit with tests; choose defaults only from diagnostics.
5. Regime breaks (book 2 ch. 5) and then the experiments (O5, O7).

## 7. Acceptance criteria and tests
* Correlation grid uses non-overlapping pairs only; counts are reported per cell; synthetic AR(1) data recovers the sign.
* Start-date sensitivity reports min/median/max of return and drawdown across offsets and is deterministic.
* Added strategy parameters are optional and leave current behaviour unchanged by default.
* ruff, mypy, existing tests green.

## Caveats
All quoted returns (Sharpe up to 5.3, APR up to 156%) are before costs and mostly on equity or futures data before 2013; several (cross-sectional stock momentum, news sentiment) collapsed or are vendor-data dependent. "Momentum crashes" and the 30-year recovery after 1929 are the strongest reminders that trend-following can stay under water for years; none of this implies that crypto trends will persist.
