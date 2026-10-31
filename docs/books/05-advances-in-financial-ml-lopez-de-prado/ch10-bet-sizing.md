# Book 5 · Chapter 10 — Bet Sizing

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 141–147 were read (strategy-independent sizing, sizing from predicted probabilities, averaging active bets, discretisation, dynamic sizing and limit prices start). Pages 148–150 (power-function alternative, exercises) were not read.

**Fit with the platform:** the platform sizes by fixed position fraction and per-trade risk (risk module), with signals that are binary (buy/sell/hold). Sizing that scales with signal confidence is new; the **discretisation** and **averaging active bets** ideas also address over-trading, which matters for fees.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | "Your ML algorithm can achieve high accuracy, but if you do not size your bets properly, your strategy will inevitably lose money." Bet size `m ∈ [−1, 1]` (−1 full short, +1 full long). Example: two strategies with identical forecasts but different sizing paths — one makes +0.5, the other loses −0.125 — because the second was forced to cut its bet as the market moved against it. | Sizing matters as much as direction. | 141 |
| C2 | **Strategy-independent sizing**: (1) **bet concurrency** `c_t = c_{t,long} − c_{t,short}` (number of active long minus short bets) mapped through the CDF of a fitted two-Gaussian mixture, so stronger-than-usual signals get larger bets and cash is reserved for signals that may still strengthen; (2) **budgeting**: size = concurrent longs ÷ max concurrent longs − concurrent shorts ÷ max concurrent shorts, so the maximum position is not reached before the last concurrent signal; (3) **meta-labeling**: the secondary model's probability sets the size. | Sizing from signal flow. | 141–142 |
| C3 | **From predicted probabilities**: for a binary side, test `H₀: p[x=1] = 1/2` with `z = (p − 1/2)/sqrt(p(1−p))`; size `m = 2 Z[z] − 1` (`Z` is the standard normal CDF); multi-class one-versus-rest with `1/X` as the null; the side comes from the predicted label. | Confidence-to-size map. | 142–143 |
| C4 | **Averaging active bets**: instead of overriding the old bet with each new one (high turnover), average sizes across all bets still active (issued before now and not yet past their end time). | Turnover control. | 144 |
| C5 | **Size discretisation**: `m = round(m/d)·d` with `d ∈ (0, 1]` to avoid trading on small changes (over-trading jitter); cap to [−1, 1]. | Fees from jitter. | 144–145 |
| C6 | **Dynamic bet sizes and limit prices**: with a forecast price `f` and current price `p`, target position `q = int(m[w, f − p]·Q)` using a sigmoid `m = x/√(w + x²)` of the divergence `x = f − p`; as `p → f` the target tends to 0 (realise gains); the **breakeven limit price** for the order is the average of the inverse function over the sizes between current and target; the width `w` is calibrated from a desired `(x, m)` pair (example: 0.95 at a divergence of 10 gives `w = x²(m⁻² − 1)`; with Q = 100, f = 115 the limit price is 112.37); power-function alternative (not read). | Sizing that avoids realising losses. | 145–147 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Position size as a function of signal strength | ❌ | Signals are discrete; size from `position_fraction` and risk-per-trade via stop distance (`assess_signal`). |
| Turnover control for sizing changes | n/a | Positions are entered and exited whole (no resizing). |
| Concurrent bets / averaging | ❌ | One position per bot at a time. |
| Dynamic limit prices | ❌ | Market orders (paper) and native stop orders (live); no limit-order entry logic (book 1 ch. 5 O2). |
| Fee impact of over-trading | ✅ (accounted) | Fees and slippage are applied on every fill; the trade count is reported. |

## 3. Opportunities

### O1 — Strength-scaled position fraction as a research option for strategies with a continuous signal *(book: C3, pp. 142–143)*
* **Proposal:** let strategies optionally emit a **conviction in [0, 1]** (e.g. normalised distance between fast and slow EMA, breakout margin in ATR units, or a model probability) and let the risk module scale the configured position fraction by `m = 2Z[z] − 1`-style or a simple clipped linear map, never above the existing caps. For long-only: `m ∈ [0, 1]`.
* **Why:** converts the binary entry into graded exposure, the closest analogue of the chapter's central point. **Caveats:** for rule-based signals conviction measures are ad hoc; the benefit must be demonstrated (compare fixed vs scaled sizing on the same signals, per risk-adjusted metric, with the whole pipeline); scaling by strength can concentrate risk at breakout extremes (where volatility is high); the risk module's per-trade risk cap still applies. **Complexity:** medium (strategy interface change: add optional conviction; engine and trader). **Validation:** conviction 1 equals current behaviour; scaled size never exceeds the cap; deterministic.

### O2 — Size discretisation (step size) to prevent micro-adjustments if resizing is ever added *(book: C5, p. 144–145)*
If positions begin to be resized (volatility sizing, scale-in/scale-out; book 4 ch. 23 O2), enforce a minimum change threshold (`d`, e.g. 10–25% of the target) and exchange minimum-notional/lot-size constraints, to avoid fee-dominated churn. **Complexity:** low; part of any resizing feature. **Validation:** no order below the step; fee drag reduced on a jittery synthetic signal.

### O3 — Fee-aware turnover metrics *(book: C4, C5)*
Report **turnover** (sum of absolute position changes per year) and **fees as a share of gross profit**, and warn when fees consume a large fraction; combined with the cost-coverage guard (book 4 ch. 16 O4, ch. 21 O6). **Complexity:** low. **Validation:** fixtures.

### O4 — Dynamic exit price logic (limit-style take-profit approach) — recorded, not recommended *(book: C6, pp. 145–147)*
The sigmoid target-position/limit-price scheme presumes a forecast price (`f`) from a model; the platform has no price forecast. If ML forecasts of barrier outcomes ever exist, revisit. Meanwhile it overlaps with the take-profit logic (book 4 ch. 23 O5: do not default to targets for trend strategies). **Complexity:** high.

### O5 — Probability-to-size mapping is the output of the meta-labeling track *(book: C2, C3)*
Part of ch. 3 O3: the secondary model's probability sets the position fraction through the book's map, with safe defaults (below threshold, no trade) and the existing caps. **Complexity:** part of the ML track.

### Not applicable
Short positions and bet concurrency netting long against short (long-only spot), Texas Hold'em analogy, mixture-of-Gaussians fitting for concurrency.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 turnover and fee-share metrics | medium | – | – | low | metrics |
| 2 | O1 strength-scaled fraction (research) | medium | medium | – | medium | strategy interface |
| 3 | O2 discretisation (with any resizing) | – | medium | – | low | resizing feature |
| 4 | O5 probability sizing | potentially high | medium | – | ML track | ML approval |
| 5 | O4 dynamic limit prices | – | – | – | high | forecast model |

## 5. Affected files
`analytics/domain/metrics.py` (turnover and fee share), `strategies/domain/types.py` (optional conviction), `risk_management/domain` (scaling), `backtesting/domain/engine.py`, `trading/application/trader.py`, app forms, tests.

## 6. Incremental plan
1. Metrics.
2. Conviction interface and experiment.
3. Discretisation when resizing exists.
4. Probability sizing with the ML track.

## 7. Acceptance criteria and tests
* Turnover and fee share match hand-computed fixtures; conviction scaling bounded by caps and identical to the present behaviour at conviction 1; ruff, mypy and existing tests green.

## Caveats
The two-Gaussian concurrency approach, the probability-to-size mapping and the sigmoid dynamic sizing are the author's constructions with illustrative numbers; no empirical performance is shown in these pages. Sizing by predicted probability is only as good as the calibration of those probabilities (not discussed in the pages read).
