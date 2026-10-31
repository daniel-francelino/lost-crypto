# Book 1 · Chapter 6 — Money and Risk Management

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

## 1. Chapter summary (pp. 95–113)

The chapter follows E. Thorp's treatment of the Kelly criterion. Chan applies it to a portfolio of *strategies*.

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Objective: maximise long-term compounded growth**, which requires avoiding ruin (if ruin has non-zero probability, long-term wealth is zero). Assumes Gaussian returns with fixed mean and standard deviation, net of financing costs (excess returns); the author states this is crude and can be inaccurate. | What "optimal" means. | 96 |
| C2 | **Kelly allocation:** `F = C⁻¹ M` (C = covariance matrix of one-period simple, unlevered excess returns; M = mean returns). For independent strategies: **`fᵢ = mᵢ / sᵢ²`**. Kelly `f` does not depend on the time scale (annual or daily inputs give the same `f`). | How much capital and leverage per strategy. | 96–97, 99 |
| C3 | **Growth rate:** for one strategy `g(f) = r + f·m − s²·f²/2`; at `f = 1`, `r = 0`, `m = 0` this gives `g = −s²/2` (Example 6.1: a ±1%-per-minute random walk loses 0.5 bp per minute although the average return is zero). At the optimum, `g = r + S²/2` with S the Sharpe ratio; multi-strategy: `g = r + FᵀCF/2`, `S = √(FᵀCF)`. Lesson: **risk always reduces long-term growth.** | Why risk management is not optional. | 97–98, 102, 112–113 |
| C4 | **Worked examples:** SPY: mean 11.23%, std 16.91%, risk-free 4% → Sharpe 0.4275, Kelly leverage 2.528, growth 13.14% (unlevered 9.8%). Three ETFs: F = (1.29, 1.17, −1.49), growth 15.29%, Sharpe 0.4751. | Numeric reference for tests. | 99–102 |
| C5 | **Half-Kelly** is common because inputs are uncertain and returns are not Gaussian. If broker leverage is capped at *l*, scale every `fᵢ` by `l / Σ|fᵢ|`. | Estimation error and limits. | 98 |
| C6 | **Rebalance as equity changes:** after a loss, Kelly says *reduce* exposure (book example on SPY: a 10% loss on a 2.528× portfolio means cutting to 2.528 × new equity); after gains, increase. Update at least daily; re-estimate `F*` from a trailing window (rule of thumb: **six months for strategies holding about a day**) — a short window also lets you phase out strategies that lose edge. For variable numbers of positions, use Kelly to set the maximum number/capital. Always safer to stay below Kelly. | Continuous risk control. | 102–103 |
| C7 | **Risk management means selling at a loss**; at scale it causes contagion (August 2007 quant losses are described). Half-Kelly reduces how much must be sold. | Cost of de-risking. | 103–105 |
| C8 | **Fat tails:** estimate the **maximum historical one-period loss** by backtest, divide the maximum tolerable one-period equity drawdown by it, and use **the smaller of half-Kelly and that leverage**. S&P example: worst day −20.47% (19 Oct 1987); with a 20% tolerance, max leverage ≈ 1 versus half-Kelly 1.26. Truly unprecedented events cannot be modelled. | Black swans. | 105–106 |
| C9 | **Stop-loss is not a universal protection** (sidebar): in a catastrophic gap the stop fills far below; stops help only in a momentum/trending regime and hurt in a mean-reverting one; moves with news tend to be momentum, moves without apparent news tend to be liquidity events that revert. Author's observation, not a proof. | Misusing stops. | 106–107 |
| C10 | **Other risks, in decreasing likelihood:** *model risk* (biases, errors, competition, regime shift; **have a collaborator replicate your backtest independently**; mitigate by lowering leverage gradually as it loses, via trailing Kelly, rather than shutting down abruptly), *software risk* (compare live trades with backtest trades), *natural-disaster risk* (Internet/power; see Ch. 4). | Non-market risks. | 107–108 |
| C11 | **Psychology:** loss aversion/status-quo bias (holding losers, closing winners too early; **exit an erroneous position immediately**), representativeness bias (retuning after a loss → any change must be backtested over a long period), despair (shutting down or doubling down) and greed (levering up after good runs). The golden rule: **keep the portfolio size under control at all times**; start small and grow. LTCM and Amaranth are cited as over-leverage failures. | Human override. | 108–111 |
| C12 | Over-leverage hits the best recent performers hardest (overconfidence). | – | 111–112 |

The chapter assumes stocks, futures and broker leverage. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| C1/C2 Kelly or any growth-optimal sizing | ❌ | No Kelly or volatility-based sizing. Size is `max_position_fraction` of equity, optionally limited by `max_order_notional`, and by `max_risk_per_trade_pct` when the signal carries a stop (`risk_management/domain/models.py::assess_signal`). |
| Leverage | n/a | Spot long-only: effective leverage ≤ 1 (`max_position_fraction ∈ (0,1]`). Kelly `f > 1` is not usable; `f < 1` would be informative. |
| C3 growth/ruin | ❌ | No growth-rate or ruin-probability estimate in any report. |
| C5 half-Kelly / conservative sizing | ⚠️ | Conservative by default only through the user's chosen fraction. |
| C6 dynamic de-risking | ❌ | Binary controls only: `max_daily_loss_pct`, `max_drawdown_pct` and `max_consecutive_losses` **pause** the bot (abrupt shutdown, the behaviour C10 warns about); no gradual size reduction as performance decays. Daily-loss and drawdown breaches are checked in `daily_loss_breached` / `drawdown_breached`. |
| C8 worst historical period loss vs tolerance | ❌ | `max_drawdown_pct` is a runtime pause threshold, not related to the historical worst one-period loss of the traded pair. |
| C9 stops | ⚠️ | Stops exist and fill with a gap-through-stop rule at the open (more conservative than filling at the stop, consistent with the sidebar), both in backtest and paper (`risk_management/domain/stops.py`). Nothing ties the choice of stop to the strategy's regime (trend vs mean reversion). |
| C10 model risk: independent replication | ❌ | Backtests are reproducible (`seed`, candle SHA-256) but no independent second implementation or cross-check. |
| C10 software risk | ❌ | Same gap as chapter 5 (no parity report). |
| C10 disaster risk | ⚠️ | Reconciler handles crashes; no documented continuity plan (chapter 4). |
| C11 intervention discipline | ⚠️ | Kill switch and controls are audited; no reason recorded (chapter 1). Post-loss strategy edits are not gated; strategy parameters of a bot can be edited (the app has an edit page), but nothing requires a backtest comparison first. |
| C11 "exit erroneous positions" | ✅ | Exits are always allowed, even with the kill switch on. |
| Over-leverage guard | ✅ | Operator-set live caps (`LiveLimits`), global exposure and open-position limits. |

## 3. Opportunities

### O1 — Kelly/volatility reference sizing as **advice, not auto-trading** *(book: C2, C3, C5, pp. 96–99 · crypto application is our adaptation)*
* **Problem:** the operator chooses `max_position_fraction` blindly; the book's central result says an optimal exposure exists and depends on edge and volatility, and that risk itself costs growth.
* **Proposal:** from a backtest's periodic returns, compute `m`, `s`, Kelly `f = m/s²` and half-Kelly; show them (together with sample size and the warning that estimates are noisy) next to the configured fraction. Cap any suggestion at 1 (spot). Do **not** apply it automatically in the first iteration.
* **Benefit:** informed sizing, and a visible warning when the chosen fraction is above Kelly (more risk, lower growth, per C3).
* **Complexity:** low (pure functions, all `Decimal`, unit-testable against the book's SPY and three-ETF examples).
* **Risks:** `m` is hard to estimate; a few good months produce large `f`; Gaussian assumption fails in crypto (fat tails), so use at most half-Kelly and prefer the C8 cap; an in-sample Kelly is as overfit as the backtest.
* **Validation:** reproduce Example 6.2 (f = 2.528, g = 13.14%) and Example 6.3 (F = 1.2919, 1.1723, −1.4882; g = 15.29%, S = 0.4751) in unit tests.

### O2 — Tail-aware leverage cap from the worst historical period loss *(book: C8, pp. 105–106)*
* **Proposal:** report, per backtest and per pair/timeframe, the largest one-period loss, and compute `max_fraction = tolerable one-period equity loss / worst historical loss`. Suggest `min(half-Kelly, max_fraction, 1)` as the exposure ceiling. The operator states the tolerable loss.
* **Benefit:** ties position size to the worst move observed. **Complexity:** low. **Risk:** history may not contain the worst event (the book says so). **Validation:** unit tests with a crash in the series.

### O3 — Gradual de-risking instead of only pausing *(book: C6, C10, pp. 103, 107)*
* **Proposal:** an optional risk mode that scales `max_position_fraction` by a trailing performance factor (for example trailing half-Kelly clipped to [0, configured fraction]) so that a decaying strategy shrinks smoothly toward zero. Keep the existing hard pauses as backstops.
* **Benefit:** avoids both abrupt shutdown at the worst moment and doubling down. **Complexity:** medium (needs a trailing-returns window in bot state, rebalancing rule for an already-open position since spot long-only can only change size at entries). **Risk:** trailing windows are noisy and can lock the bot at zero; whipsaw; applies only to new entries unless partial exits are added. **Validation:** simulated equity series with a decaying edge must show decreasing fractions; deterministic unit tests.

### O4 — Stop policy by regime *(book: C9, pp. 106–107; deeper in Ch. 7)*
* **Proposal:** record in each strategy's metadata whether it is trend-following or mean-reverting, and warn when a tight stop is combined with a mean-reverting strategy (and when a trend strategy has no stop). Existing strategies (EMA crossover, Donchian breakout) are trend/breakout. **Complexity:** low. **Risk:** the chapter's argument is the author's observation; present it as guidance, not a rule. Revisit with Chapter 7 (exits).

### O5 — Independent replication of backtests *(book: C10, p. 107)*
* **Proposal:** a small, independent vectorised reference implementation (different code path, e.g. in the test suite) that reproduces key backtest outputs for the shipped strategies on fixed fixtures; any difference fails tests. Cheap approximation of the "collaborator" the book recommends. **Complexity:** medium. **Validation:** it is itself the validation.

### O6 — Discipline guards on parameter edits *(book: C11, pp. 109–110 · adaptation)*
* **Proposal:** when editing a running bot's strategy parameters, show the last backtest comparison of old vs new parameters and require a reason (ties to Chapter 1 O3); record in audit. Do not block. **Complexity:** low–medium. **Risk:** friction ignored by habit.

### O7 — Ruin/exposure summary for the operator *(book: C1, C3, C11)*
* **Proposal:** portfolio view showing current exposure vs Kelly reference vs live caps, so "keep the portfolio size under control at all times" is observable. Depends on O1/O2. **Complexity:** low.

### Not applicable / deferred
Multi-strategy covariance allocation `F = C⁻¹M` (one pool, independent bots; revisit when several strategies share capital), broker leverage scaling (no leverage), contagion discussion, Amaranth/LTCM anecdotes (illustrations only).

## 4. Priority

| # | Item | Risk mgmt | Reliability | Backtest quality | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O2 worst-period-loss cap | **high** | – | – | low | metrics (chapter 2) |
| 2 | O1 Kelly reference (advice) | high | – | medium | low | Sharpe/returns series |
| 3 | O5 independent replication | medium | **high** | high | medium | – |
| 4 | O7 exposure summary | medium | – | – | low | O1, O2 |
| 5 | O6 parameter-edit guard | medium | medium | – | low–med | chapter 1 O3 |
| 6 | O4 stop-regime hint | low | – | – | low | strategy metadata |
| 7 | O3 gradual de-risking | high | – | – | medium | O1; separate design |

## 5. Affected files
`analytics/domain/` (new pure functions: returns series, Kelly, worst period loss), `analytics/presentation/schemas.py`, `backtesting/application/service.py` and `router.py` (additive fields), `risk_management/domain/models.py` (only for O3), `strategies/domain/base.py` (metadata for O4), `bots/application/service.py` (O6), tests under `api/tests/unit`, app: backtest detail and bot risk form (hints), `docs/openapi.json`.

## 6. Incremental plan
1. Pure functions for returns, Kelly and worst period loss with the book's examples as tests.
2. Expose them in backtest results as optional fields; show in the app next to the chosen fraction.
3. Reference-implementation cross-check test (O5).
4. Exposure summary (O7) and parameter-edit guard (O6).
5. Gradual de-risking (O3) as its own design after the above has run for a while.

## 7. Acceptance criteria and tests
* Unit tests match Examples 6.2 and 6.3 within rounding and Example 6.1 (`g = −s²/2`).
* Kelly output is `None` for too few returns or zero variance, never infinite; always shown with sample size.
* Suggested exposure never exceeds 1 and never exceeds the operator's live caps.
* No existing risk behaviour changes unless an opt-in mode is enabled; live safeguards untouched.
* Everything is `Decimal`; ruff, mypy, existing tests green.

## Caveats
Kelly sizing assumes known, stable, Gaussian returns; crypto has fat tails, regime changes and estimation error, so a Kelly figure is an **upper bound to be discounted**, never a recommendation to size up. The author's anecdotes (LTCM, Amaranth, his own losses) illustrate behaviour and are not evidence for the formula. Past volatility does not bound future losses.
