# Book 1 · Chapter 2 — Fishing for Ideas

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

## 1. Chapter summary (pp. 9–29)

The chapter is a set of **quick screens** to apply to a candidate strategy before backtesting it.

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Ideas are abundant (papers, blogs, forums); most ready-made ones do not survive careful backtesting (stopped working, only small caps, ignore costs). A basic idea can often be modified into a profitable one; the proprietary part is the variation. | Where to find strategies and how sceptical to be. | 9–11 |
| C2 | Fit the strategy to *you*: working hours, programming skill, capital, goal (income vs long-term gain). Holding period drives income regularity. | Strategy that cannot be operated by its owner. | 12–17 |
| C3 | Maximum long-term growth comes from the maximum **Sharpe ratio** (given enough leverage), not from buy-and-hold; a higher Sharpe allows more leverage (details deferred to Ch. 6). | Judging strategies by raw return. | 17, 19 |
| C4 | Compare with a **benchmark**: for long-only, the market index; for dollar-neutral, a riskless rate. `Information Ratio = mean(excess returns) / std(excess returns)`, `Excess = portfolio − benchmark`. Sharpe is the special case with the risk-free rate; people use Sharpe for comparability. | Return without context and without consistency. | 18–19 |
| C5 | Rules of thumb: few trades a year → low Sharpe; drawdown deeper than ~10% or longer than ~4 months → unlikely high Sharpe; **Sharpe < 1 is not suitable stand-alone**; profitable almost every month → annualised Sharpe typically > 2; almost every day → > 3. | Quick triage from limited information. | 20–21 |
| C6 | **Drawdown** = current equity − running maximum (the *high watermark*); maximum drawdown = largest peak-to-trough fall, in % of the watermark; **maximum drawdown duration** = longest time to recover; the two usually do not overlap. Compare them with your own tolerance. | Strategy you cannot psychologically hold. | 21–22 |
| C7 | **Transaction costs** = commissions + bid-ask spread (liquidity cost) + market impact + slippage (delay between trigger and execution). Limit orders avoid spread but cost missed trades. Estimate cost ≈ half the average spread (+ commission) if order size is small. Example: a 5-minute Bollinger mean-reversion on ES goes from Sharpe ≈ 3 to ≈ −3 after 1 bp of cost. | High-frequency edges that vanish after costs. | 22–23 |
| C8 | **Survivorship bias**: data lacking delisted/bankrupt names inflates results, especially for "buy cheap" ideas; ask for point-in-time data. | Inflated backtests. | 24 |
| C9 | **Performance over time**: older periods look better (less competition, wider spreads, more survivorship distortion); judge by the most recent years. **Regime shifts** break stationarity, so more data is not automatically more robust. | Trusting a long, heterogeneous sample. | 24–25 |
| C10 | **Data-snooping bias**: many parameters/rules → fit to accidents; hard to avoid even with one or two parameters. Simple models last. The AI sidebar lists his conditions for models he trusts: sound rationale, few parameters, linear, simple, all optimisation in a **lookback moving window** with continued out-of-sample demonstration. Independent financial data is scarcer than it looks (tick data is serially correlated). | Overfitting. | 25–27 |
| C11 | **Capacity/niche**: prefer strategies too small for institutions. | Competition from large players. | 27 |

Not in this chapter: how to compute annualised Sharpe or drawdown in practice (Ch. 3, Examples 3.4–3.7). Chan gives no crypto guidance; crypto points are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| C4 benchmark | ✅ partly | `buy_and_hold_return_pct` exists (`analytics/domain/metrics.py`). It is a return comparison only; no excess-return series, no information ratio. |
| C3/C4/C5 Sharpe | ❌ | No Sharpe/Sortino/volatility/annualised return in `Metrics`. |
| C6 drawdown | ⚠️ | `max_drawdown_pct` exists (peak-to-trough, % of watermark, matches the book's definition). **Duration is not computed**, nor the high-watermark series. |
| C7 costs | ⚠️ | Fixed `fee_rate` + fixed `slippage_bps`, same code in backtest and paper (`execution/domain/fills.py`). No sensitivity to cost level, no break-even cost, no size-dependent impact; limit-order opportunity cost not modelled. Market orders only in the backtester. |
| C8 survivorship | ⚠️ | Crypto pairs can be delisted too; candles are stored per symbol and a symbol list is chosen by hand, so a hand-picked "survivors" universe is likely. No delisting handling. Not applicable to a single-pair backtest, relevant when we compare pairs. |
| C9 over time | ⚠️ | One chronological train/test split (`backtesting/domain/segments.py`). No per-year/sub-period breakdown, no rolling windows, no regime labelling. |
| C10 snooping | ⚠️ | Strategies have 2–4 parameters (good). Sweeps rank by a single metric with **no count of trials** and no correction; train/test split exists but is a single hold-out. |
| C2 fit to operator | ✅ | Timeframe-based bots, automation, worker; documented in architecture docs. |
| C11 niche | n/a | Capital is small by design; no capacity model needed now. |

## 3. Opportunities

### O1 — Add Sharpe, Sortino, volatility, annualised return to `Metrics` *(book: C3–C5, pp. 17–21 · crypto annualisation is our adaptation)*
* **Problem:** cannot apply the book's own screening rules (Sharpe < 1, ratio vs benchmark) or compare strategies on risk-adjusted terms.
* **Proposal:** compute from the equity curve's periodic returns. Annualisation factor derived from the candle timeframe and **365 days** (crypto trades every day, unlike the book's stock examples; the exact convention is the subject of Chapter 3, so settle it there). Risk-free rate configurable, default 0. Mark metrics `None` when there are too few returns.
* **Benefit:** the single most useful missing number; enables comparison of sweep results and ranking by something better than net PnL.
* **Complexity:** low–medium (pure functions, all `Decimal`; careful with square roots and equity curves that sit flat while out of the market).
* **Risks:** Sharpe on few, autocorrelated or flat-heavy returns is misleading; a high Sharpe from a short sample is not evidence. Must display sample size beside it.
* **Validation:** unit tests with hand-computed series; property: scaling returns scales Sharpe correctly; zero-variance returns give `None`, not infinity.

### O2 — Drawdown duration and high-watermark series *(book: C6, p. 21)*
* **Problem:** only depth is reported; the book treats duration as equally important to whether the operator will hold on.
* **Proposal:** add max drawdown duration (bars and wall-clock) and expose the underwater curve for the app chart.
* **Benefit:** answers "how long can this stay under water?". **Complexity:** low.
* **Risk:** open drawdown at the end of the series must be reported as ongoing, not as recovered.
* **Validation:** unit tests including a series that never recovers.

### O3 — Operator tolerance check *(book: C6 p. 22 · adaptation to a product feature)*
* **Proposal:** let the operator state maximum acceptable drawdown (depth, duration) when creating a backtest/bot; flag runs that exceed it. `max_drawdown_pct` already exists as a *runtime* risk limit; this would connect research to it.
* **Complexity:** low. **Risk:** false comfort if the backtest drawdown is itself understated. **Validation:** API test for the flag.

### O4 — Cost-sensitivity analysis *(book: C7, pp. 22–23)*
* **Problem:** a fixed cost assumption can hide a strategy that dies at slightly higher costs, which is exactly the book's ES example.
* **Proposal:** re-run (or cheaply recompute) the same signals under a grid of fee/slippage values; report net result per level and the **break-even cost**. A sweep dimension may already allow this, so check before building.
* **Benefit:** direct robustness gain for the backtests. **Complexity:** medium (cost scales run time; cache signals).
* **Risks:** only changes costs, not fill realism (market impact, queue position for limit orders).
* **Validation:** a strategy engineered to be marginal must flip sign at a known cost.

### O5 — Performance by sub-period *(book: C9, pp. 24–25)*
* **Proposal:** report metrics per calendar year/quarter and for the most recent window, plus a "recent vs overall" flag, in addition to the single train/test split.
* **Benefit:** detects decay and regime dependence. **Complexity:** low–medium. **Risk:** small sub-samples are noisy; label sample sizes. **Validation:** synthetic series with a break in the middle.

### O6 — Count the trials in sweeps *(book: C10, pp. 25–27)*
* **Problem:** ranking N parameter sets and showing the winner overstates its quality; the book names the bias but defers the remedy to Chapter 3 (and later books give formal corrections).
* **Proposal (minimum):** record number of combinations tried on every sweep result and show it next to the best result; require the winner to also be acceptable on the held-out test part. No new statistics yet.
* **Complexity:** low. **Validation:** API response includes the trial count.

### O7 — Survivorship/universe note *(book: C8, p. 24 · adaptation)*
Add an explicit warning when comparing several pairs chosen after the fact, and record the listing history needed to detect delistings when more pairs are imported. Low priority until multi-pair research exists.

### Not recommended now
* **Lookback-window optimisation (C10, p. 27)** is the book's recommended discipline (walk-forward). It is a larger feature and is better planned after Chapter 3 and the later books on cross-validation; recorded as backlog **B-WALK-FORWARD**.
* **Sharpe-based leverage (C3)**: no leverage exists.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 Sharpe/Sortino/vol | high | medium | – | low–med | Ch. 3 annualisation convention |
| 2 | O2 DD duration | medium | high | – | low | – |
| 3 | O6 trial count | high | – | – | low | sweeps (exist) |
| 4 | O4 cost sensitivity | high | medium | – | medium | O1 |
| 5 | O5 sub-periods | medium | – | – | low–med | O1 |
| 6 | O3 tolerance flag | low | medium | – | low | O2 |
| 7 | O7 universe note | low | – | – | low | – |

## 5. Affected files
`api/src/modules/analytics/domain/metrics.py`, `analytics/presentation/schemas.py`, `backtesting/domain/segments.py`, `backtesting/application/service.py`, `backtesting/presentation/router.py`, sweep result schema, `docs/openapi.json`, app: `lib/backtests` schemas, metric cards, equity/underwater chart (`equity-chart-rows.ts`), `check:consistency`.

## 6. Incremental plan
1. Pure metric functions + unit tests (O1, O2) with no API change.
2. Add fields to `Metrics.to_dict` (additive, optional) and to the OpenAPI doc; app shows them.
3. Sweep trial count (O6).
4. Cost-sensitivity run (O4).
5. Sub-period report (O5).
6. Tolerance flag (O3).

## 7. Acceptance criteria and tests
* Existing metrics and stored runs unchanged (additive fields only); old runs show "n/a" for new ones.
* Hand-computed fixtures for Sharpe, Sortino, drawdown duration (including never-recovered).
* All numbers stay `Decimal`; no float in the domain.
* Sweep output includes the number of combinations.
* The new metrics always show their sample size; none is presented as a guarantee of future returns.

## Caveats
Chan's thresholds (Sharpe > 1, > 2, > 3; drawdown 10% / 4 months) are **rules of thumb from his stock/futures experience**, not laws, and were not calibrated on crypto. Use them only as initial triage defaults, configurable.
