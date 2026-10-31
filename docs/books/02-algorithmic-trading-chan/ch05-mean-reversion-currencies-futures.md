# Book 2 · Chapter 5 — Mean Reversion of Currencies and Futures

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 107–131 was read.

This chapter is almost entirely about foreign-exchange cross-rates and exchange-traded futures (roll returns, calendar spreads, volatility futures). Lost Crypto is spot, long-only, one asset per bot, so **most of it is not applicable today**. The report records what is relevant now and what becomes relevant if derivatives are ever added. Backtests in the chapter exclude costs (p. 64 caveat applies).

## 1. Chapter summary (pp. 107–131)

| ID | Concept | Pages |
|---|---|---|
| C1 | Currencies and futures are momentum territory; mean reversion is the exception. Currency pairs of "commodity currencies" can cointegrate. Currencies have higher liquidity, no short-sale constraints, and trade around the clock (Sunday 5 pm to Friday 5 pm ET), so **stop-losses are meaningful because the market does not gap across long closures**. | 107–108 |
| C2 | FX mechanics: base/quote currency; synthetic crosses (`USD.ZAR/USD.AUD`) produce P&L in two currencies that must be converted regularly or live results drift from the backtest; for Johansen/regressions, point moves must have the same value (use a common quote currency); return formulas differ by the quote/base structure. Example 5.1 (AUD.USD vs CAD.USD, 250-day training, Johansen hedge ratio): APR 11%, Sharpe 1.6. | 108–113 |
| C3 | **Rollover interest** (overnight financing) adds `log(1+i_B) − log(1+i_Q)` to the return of a held cross-rate, tripled over weekends by settlement rules; **excess return = return − financing cost**, which is zero for intraday positions, dollar-neutral equity, and futures; Example 5.2 (AUD.CAD): APR 6.2%, Sharpe 0.54; neglecting rollover would have shown 6.7% even though the average rollover was almost 5%/year. | 113–115 |
| C4 | **Futures returns = spot return + roll return**; backwardation (near > far, positive roll) vs contango (negative roll); model `F(t,T) = c·e^{γt}·e^{λ(t−T)}`; spot and roll returns estimated by regression (Example 5.3); for BR, C and TU the roll return magnitude exceeds the spot return (e.g. corn: roll −12.8% vs spot 2.8%). Mean reversion of a spot price does not imply mean reversion of the futures price (the author lost >$100,000 in 2006 on an ETF-vs-futures-fund pair; VX is in contango about 3/4 of the time with an average roll of about −50%/year). | 115–122 |
| C5 | **Calendar spreads** of traded assets mean-revert only through the roll return: CL 12-month spread, ADF 99%, half-life 36 days, APR 8.3%, Sharpe 1.3 (Example 5.4); VX spread via the ratio, APR 17.7%, Sharpe 1.5 but poor before Oct 2008. | 123–127 |
| C6 | **Intermarket spreads** rarely mean-revert (crack spread and CL/BZ failed ADF; structural reasons such as pipeline bottlenecks and sanctions). Synchronous closing times matter. | 127–129 |
| C7 | **VX vs ES**: volatility futures are anti-correlated with the index; the relationship has **two regimes** (2004–May 2008, Aug 2008–2012); **running a regression or Johansen test on a mixture of regimes would be a mistake**, so the author fits only the second regime (first 500 days as training); APR 12.3%, Sharpe 1.4 on the test set (Jul 2010–May 2012). | 129–131 |

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| FX crosses, rollover, synthetic pairs | n/a | Spot crypto: no overnight interest on holding the purchased asset; quote currency is a stablecoin or BTC. |
| Futures, roll return, calendar spreads, VX | n/a | No derivatives in `exchanges` (spot and testnet spot only). |
| Excess return net of financing | ✅ n/a | Long-only unlevered spot has no financing cost; metrics are net of fees and slippage (`analytics/domain/metrics.py`). |
| Stops useful because the market is continuous | ✅ | Crypto spot trades 24/7; the stop model fills a gap-through at the open (`risk_management/domain/stops.py`), which is conservative for illiquid pairs. |
| Regime mixture in a single fit | ❌ | Backtests run over whole ranges with no regime split; `test_fraction` splits only chronologically. |
| Currency conversion of realised P&L to a base | ⚠️ | Each bot reports PnL in its quote currency; the dashboard groups totals per currency instead of converting (`GET /bots/summary`). No FX/valuation currency is attempted. |

## 3. Opportunities

### O1 — Regime-aware evaluation: do not fit or judge across a structural break *(book: C7, pp. 129–130)*
* **Problem:** a backtest, a half-life or a hedge ratio estimated over a window that straddles a regime change is invalid (the VX/ES example). Crypto has clear candidates (2017–2018 cycle, May 2021 crash, the 2022 collapse).
* **Proposal:** let the operator mark **break dates** (named, per exchange or global) and report metrics per regime as well as overall; let diagnostics (book 2 ch. 2 O1) and sweeps run on a chosen regime only; display a warning when a run's date range spans a registered break. Detecting breaks automatically is *not* proposed (book 1 ch. 7 explains why regime prediction is unreliable).
* **Benefit:** avoids pooling incomparable periods and supports the book 1 ch. 2 point that recent data matters more. **Complexity:** low–medium (small table of named breaks, metrics by segment; extends `segments.py`). **Risk:** the choice of break dates is itself a researcher degree of freedom (snooping); record them before running experiments. **Validation:** synthetic series with a break; metrics per regime reproduce direct computation.

### O2 — Keep the stop-loss fill model conservative and test it *(book: C1, p. 108 · confirms existing behaviour)*
No change proposed. Add a unit test (if none exists) that a gap through the stop fills at the open, and one on thin pairs showing the worst realistic slippage. Check `tests/unit` before adding duplicates. **Complexity:** very low.

### O3 — Backlog if derivatives are added: perpetual-futures funding and basis as the "roll return" *(book: C3–C5, pp. 113–127 · adaptation, speculative)*
If perpetual futures or dated futures are ever supported, three concepts transfer almost directly: total return = price return + funding/roll return; excess returns must include the funding cost when computing Sharpe; and spot-based intuition (for example "the spot reverts, so the contract reverts") can be wrong because of that carry. Record as **B-DERIVATIVES**; nothing to do now. Adding derivatives would also reopen leverage (book 1 ch. 6), shorting and liquidation risk, which the current safeguards do not cover.

### Not applicable
Currency base/quote mechanics, cross-rate synthetic construction, rollover rates, calendar and intermarket futures spreads, crack spread, volatility futures strategies.

## 4. Priority

| # | Item | Backtest quality | Reliability | Risk mgmt | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 regime-aware evaluation | high | – | – | low–medium | book 1 ch. 2 O5 (sub-period metrics) |
| 2 | O2 stop-fill tests | low | medium | low | very low | – |
| 3 | O3 derivatives backlog | – | – | – | n/a | product decision |

## 5. Affected files
`backtesting/domain/segments.py`, `backtesting/application/service.py`, a small table/ORM for named breaks (`backtesting` or `market_data` module), router and schemas, `docs/openapi.json`, app backtest form and detail, tests.

## 6. Incremental plan
1. Sub-period metrics (book 1 ch. 2 O5).
2. Named break dates, per-regime metrics and warnings.
3. Stop-fill tests.

## 7. Acceptance criteria and tests
* Metrics per regime equal those computed directly on the same sub-series.
* A run spanning a registered break shows a warning; no change to trading behaviour.
* ruff, mypy, existing tests green.

## Caveats
Numbers quoted (APR 6.2–17.7%, Sharpe 0.54–1.6, roll returns) are 2002–2012 FX/futures examples without costs and in part in-sample; they say nothing about crypto spot.
