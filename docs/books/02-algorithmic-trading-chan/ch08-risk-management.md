# Book 2 · Chapter 8 — Risk Management

*Algorithmic Trading*, Chan (2013). Book pages (PDF = book + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only. All of pp. 169–186 was read. Builds on [book 1 ch. 6](../01-quantitative-trading-chan/ch06-money-and-risk-management.md).

## 1. Chapter summary (pp. 169–186)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Objective: **maximise long-term equity growth**; avoid risk only insofar as it harms that. Loss aversion (needing about $2 of upside per $1 of downside, Kahneman) explains why a Sharpe of 2 feels good, but is not rational on its own. | Framing risk. | 169 |
| C2 | **Optimal leverage assumptions**: the future return distribution equals the past one; stricter versions: the strategy's own distribution is unchanged; strictest: Gaussian. Optimal leverage implies no ruin in history; a maximum drawdown limit becomes an extra constraint. **Leverage must be kept constant**, which means *selling into losses* and buying into gains (Example 8.1: leverage 5, equity 100K → 90K forces selling to 450K); this "selling into losses" is blamed for contagion in the August 2007 quant crisis. | Constant-leverage discipline. | 170–171 |
| C3 | **Kelly** `f = m/σ²` (Gaussian). Overestimated mean or underestimated variance → overestimated leverage → eventual ruin; underestimation only reduces growth, so traders use **half-Kelly**. In the author's experience Kelly is **an upper bound**: backtest Kelly often exceeds broker limits or would have ruined the account in backtest because returns are not Gaussian; Russell 1000/2000 Kelly ≈ 1.8 vs 3× ETFs. Multi-strategy: `F = C⁻¹M`; under a maximum-leverage cap, uniform scaling is not optimal; Example 8.2 (two strategies, cap 2): all buying power on the highest-growth strategy gave g = 0.96 vs 0.82 scaled. | Sizing. | 172–175 |
| C4 | **Monte Carlo optimisation of growth**: `g(f) = ⟨log(1 + f·R)⟩` over simulated per-bar returns R drawn from a **Pearson-system** distribution matching mean, standard deviation, skewness and kurtosis of the strategy's returns; maximise numerically. Example: Kelly 18.4, Monte Carlo ≈ 19, historical optimisation also 18.4; leverage above 1/|worst return| (30.2) gives −100%. Directly optimising on historical returns suffers data-snooping but here agreed with the other two. | Fat-tailed sizing. | 175–178 |
| C5 | **Maximum drawdown constraint**: not linear in leverage; the unconstrained optimum had a −99.9% simulated drawdown; half of it still −96.3%; ~7× lower leverage (2.7) needed for −50%; historical returns needed only ÷1.5. Simulated returns give statistical power but may miss serial correlation and describe once-in-a-million-years events; historical returns capture correlation but have too little data; **a compromise between the two is suggested**. Leverage limits do not *guarantee* future drawdown limits. | Drawdown budgeting. | 179–180 |
| C6 | **CPPI** (constant proportion portfolio insurance): set aside `D` (the maximum drawdown allowed) as the trading sub-account and apply Kelly leverage `f` to it; the rest sits in cash; **raise the sub-account back to D of total equity only at new high-water marks, never top it up after losses**; if the sub-account is exhausted, retire the strategy (a principled wind-down). Same growth as an equivalent fixed leverage in the author's simulation (0.002484 vs 0.002525 per day) but the drawdown is bounded below `D` (0.5 vs 0.9). Applies to **one strategy per account**; cannot protect against gaps or suspended trading. | Bounded drawdown with growth. | 180–182 |
| C7 | **Stop-loss**: per-position vs strategy-level (awkward, one-time; CPPI preferred). Works only when the market is open while you hold; fails when liquidity vanishes (2010 flash crash stub quotes: an Accenture stop sold at $0.01). For **mean-reverting** strategies stops lower backtest performance, but that is partly **survivorship bias** (strategies whose regime changed to trending never made it into the catalogue). Recommendation: set the stop **beyond the largest backtest intraday drawdown**, so it never fires in the backtest and only guards against a black swan. For **momentum** strategies the opposite signal is a de facto stop, so tail risk is lower. | Using stops sensibly. | 182–184 |
| C8 | **Leading risk indicators** (VIX, TED spread, HYG, MXN, ONN/OFF, order flow): proactive avoidance of risky periods; strategy-specific (VIX > 35 *helped* the buy-on-gap strategy and *destroyed* the FSTX gap strategy: Sharpe 1.4 → 0.16); crises are rare so indicators are easily data-snooped. | Avoiding bad periods. | 184–186 |
| C9 | Conclusion: judgment calls remain (lowering leverage before a known event: author says no if the model survived earlier stress; allocate Kelly **per strategy** so poor ones die quickly rather than across a pool); regime shifts, not backtest pitfalls, are often why live diverges; hypothesis → model → test on unseen data. | Judgment vs rules. | 187–189 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Constant leverage / equity-proportional sizing | ✅ spot | Entries are sized as a fraction of **current bot equity** (`equity * max_position_fraction` in `assess_signal`), so size shrinks after losses and grows after gains without an explicit rebalance. Leverage ≤ 1. |
| Kelly / Monte Carlo growth optimisation | ❌ | Nothing computes `m/σ²`, `g(f)` or simulated optimisation. |
| Drawdown as a function of exposure | ❌ | No analysis of how drawdown scales with `max_position_fraction`. |
| Stops: native exchange stop orders live | ✅ | `trader.py:189-196`: "a stop resting on the exchange is the authority". Paper/backtest use the gap-through-open model. |
| Stops: never-in-backtest placement rule | ❌ | `stop_loss_pct` is user-chosen; no check against the backtest's worst adverse excursion. |
| Strategy-level drawdown stop | ✅ | `max_drawdown_pct`, `max_daily_loss_pct`, `max_consecutive_losses` pause the bot (`risk_management/domain/models.py`, `trader.py:550-568`). |
| CPPI-style sub-account | ⚠️ partial | Each bot is a virtual sub-account with its own capital (`bot_portfolios`), the reconciler enforces that the exchange account holds at least the sum of bot books. There is **no ratchet** (raising allocation at new high-water marks, never after losses) and no automatic retirement rule tied to a drawdown budget beyond the pause. |
| Per-strategy rather than pooled allocation | ✅ | Bots are independent. |
| Leading risk indicators | ❌ | No external indicators; the only market-based guard is `max_candle_range_pct` (entry-time). |
| Max exposure caps | ✅ | `max_position_fraction`, `max_order_notional`, global exposure and live caps. |

## 3. Opportunities

### O1 — Growth-rate and drawdown curves vs exposure from backtest returns *(book: C3–C5, pp. 172–180)*
* **Problem:** `max_position_fraction` is picked blindly. The chapter's machinery tells how growth `g(f)` and maximum drawdown change with exposure.
* **Proposal:** from a backtest's per-bar returns compute, over exposure `f ∈ (0, 1]` (cap of 1 because spot): (a) the empirical growth rate `⟨log(1+f·R)⟩`, (b) the maximum drawdown with that exposure, (c) a flag when `f` exceeds the Kelly value or half-Kelly. Show as a small curve/table beside the bot's configured fraction. Use historical returns first; add a **bootstrap of the empirical per-bar returns** as the "simulated" counterpart (our adaptation: resampling avoids needing the Pearson system, and it keeps skew and kurtosis without fitting a family; it destroys serial correlation, which the book also points out for simulated returns).
* **Benefit:** concrete numbers for sizing and drawdown budgeting; replaces guesswork. **Complexity:** medium (log-growth in `Decimal` or a documented float boundary; bootstrap needs a seeded RNG).
* **Risks:** results are only as good as the sample (book: historical optimisation is snooped and simulations describe unobserved extremes); returns in crypto are volatile and autocorrelated; presenting a single "optimal" value invites over-confidence, so present a range and keep Kelly as an upper bound, as the author does.
* **Validation:** reproduce Example 8.2's two-strategy numbers for the Gaussian case; known synthetic returns where `g(f)` peaks at the analytic Kelly; seeded determinism; leverage above `1/|worst return|` yields ruin.

### O2 — CPPI-style "risk budget" per bot *(book: C6, pp. 180–182 · adaptation to our bot sub-accounts)*
* **Problem:** a bot's loss is limited only by pauses and caps; the book proposes a principled structure that bounds drawdown by design and winds a failing strategy down.
* **Proposal:** give each bot a **risk budget `D`** (fraction of the allocated capital that may be lost). Only the budget is "at risk"; when the bot's equity makes a new high-water mark, the budget is reset to `D` of equity (ratchet); after losses it is never topped up; if the budget is exhausted, the bot stops permanently with a clear reason and audit entry. In spot long-only terms the position size is `exposure × budget`. This is a thin layer on the existing `RiskLimits` (it generalises `max_drawdown_pct` from "pause" to "retire with a ratchet").
* **Benefit:** a bounded, explainable maximum loss per bot and an end-of-life rule for decaying strategies. **Complexity:** medium (state: high-water mark, current budget; interaction with reset, manual capital changes, live approvals).
* **Risks:** gaps can still exceed the budget (book, p. 182); spot sizing already shrinks with equity so the extra protection is smaller than in the levered example; ratchet logic is easy to get wrong; applies per bot only (the book warns pooled accounts let winners subsidise losers). **Validation:** deterministic unit tests of the ratchet and of retirement; property test that realised loss never exceeds the budget on a no-gap series; no change when the feature is off.

### O3 — Stop placement relative to backtest adverse excursion *(book: C7, pp. 183–184)*
* **Problem:** a stop tighter than the strategy's normal drawdown fires inside ordinary noise and silently changes what was backtested; a looser one is the book's recommended "black-swan only" stop for reversion strategies.
* **Proposal:** compute and report the largest **adverse excursion** (worst unrealised loss within a trade) from a backtest and compare it with the configured `stop_loss_pct`; warn if the stop is inside the historical excursion and explain what that means for each strategy family (momentum: stop is part of the signal; reversion: stop beyond the worst excursion). **Complexity:** low–medium (engine must track the in-trade low). **Validation:** synthetic trades with known excursions.

### O4 — Stop-failure awareness in crypto *(book: C7, pp. 182–183 · adaptation)*
* The book shows that stops can execute at absurd prices during liquidity withdrawal. Crypto has analogous flash events. The system already uses native exchange stops live and sizes with slippage; add an alert when a protective exit fills far beyond its planned price (needs book 1 ch. 5 O4 execution records) and a documented policy on stop order types (stop-market vs stop-limit) with its trade-offs. **Complexity:** low–medium. **Depends on:** book 1 ch. 1 O1 (alerts) and ch. 5 O4.

### O5 — Per-strategy sizing, not pooled Kelly *(book: C9, p. 188)*
Confirms the current design (independent bots). Do not build pooled covariance allocation; this is a **non-change**, recorded to prevent future drift. Keep **B-PORTFOLIO** as a possible later topic, only if bots share capital.

### O6 — Risk indicators: exploratory only *(book: C8, pp. 184–186 · adaptation)*
* The book's indicators are stock/credit based. Crypto candidates (market-wide realised volatility, BTC drawdown, funding rates) are our ideas, not the book's. Given the author's warning about data-snooping on rare crises, only a **descriptive** step is proposed: report the strategy's performance split by a pre-registered volatility regime (book 2 ch. 5 O1) and do not gate trading on it until it holds out of sample. **Complexity:** low. Record as **H-RISK-INDICATOR**.

### O7 — Document the judgment calls *(book: C9, pp. 188–189)*
Write down, in the operator runbook, the policy decisions the author calls judgment: whether to reduce size before known events, per-strategy vs pooled sizing, and when to retire a model. Pure documentation. **Complexity:** very low.

### Not applicable
Broker leverage caps, short exposure, VIX/TED/HYG/ONN indicators as given.

## 4. Priority

| # | Item | Risk mgmt | Backtest quality | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 stop vs adverse excursion | high | medium | – | low–medium | engine change |
| 2 | O1 exposure curves | high | medium | – | medium | book 1 ch. 2 O1 (returns series) |
| 3 | O2 CPPI risk budget | **high** | – | medium | medium | O1 for choosing `D` and exposure |
| 4 | O4 stop-failure alert | medium | – | medium | low–medium | book 1 ch. 1 O1, ch. 5 O4 |
| 5 | O7 policy documentation | medium | – | – | very low | – |
| 6 | O6 regime descriptive report | low | medium | – | low | book 2 ch. 5 O1 |
| – | O5 | non-change | | | | |

## 5. Affected files
`backtesting/domain/engine.py` (adverse excursion), `analytics/domain/` (growth and drawdown vs exposure, bootstrap), `risk_management/domain/models.py` and `trading/application/trader.py` (O2 only), `bots/domain/models.py` (budget state), migrations, `docs/openapi.json`, app bot risk form and backtest detail, `docs/` runbook, tests.

## 6. Incremental plan
1. Adverse-excursion metric and the stop warning.
2. Exposure-vs-growth/drawdown curves (historical first, bootstrap second).
3. CPPI risk budget as an opt-in per bot; paper trading only until proven.
4. Execution-record based stop-failure alert.
5. Documentation of judgment policies.

## 7. Acceptance criteria and tests
* Reproduce the chapter's Kelly, `g(f)` and constrained-allocation numbers on the book's stated inputs.
* CPPI ratchet: budget rises only at new high-water marks; never after losses; retirement is triggered when exhausted; no effect when disabled.
* Live safeguards, kill switch and approvals are untouched; ruff, mypy, existing tests green.
* UI language never presents a computed "optimal" exposure as a recommendation without its caveats.

## Caveats
All Kelly, Monte Carlo and drawdown figures are for one futures-like strategy with an exposure of 18× (Example 5.1 strategy) and say nothing about spot crypto. The author states that Kelly is an upper bound, the Gaussian assumption is unreliable, leverage limits do not guarantee future drawdown, and CPPI cannot protect against gaps (pp. 172, 179, 182). Past returns are not a guarantee of future behaviour.
