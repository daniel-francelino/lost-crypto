# Book 4 · Chapter 23 — Risk Control

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 1027–1061 and 1070–1075 (luck vs skill, risk preference, risk measures, VaR, leverage, target volatility, position sizing, stops and profit targets, efficiency-ratio market selection, risk of ruin) and 1085–1093 (equity trends, optimal f, start of expected-vs-actual) were read. The directional-movement/ADX/Commodity Selection Index material (1062–1069), the sections on entering, averaging into and compounding a position (1076–1084) and the end of "Comparing expected and actual results" (1093–1098) were seen by headings only and are **not** summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Mistaking luck for skill**: a windfall from a price shock is luck; assess how the account would have survived the same move in the opposite direction; LTCM explained away past shocks and failed at the next. The only reduction of shock risk is **being out of the market** (a strategy in the market 40% of the time has a 60% chance to avoid a shock) and **earning as much as possible while investing as little as possible** (a fully leveraged program returning 200% is a total loss after a shock; a deleveraged one returning 20% is ten times more likely to survive). | Survival over return. | 1027–1028 |
| C2 | **Risk preference and utility** (Bernoulli): investors differ; the efficient frontier and the tangent point of best return/risk; the optimal point is not for everyone because absolute risk or return may be unacceptable. **Common-sense rules**: risk a small part of capital per trade (never more than 5%; elsewhere 3%); know the exit in advance; large profits mean large risk; exit quickly; **don't meet margin calls**; liquidate the worst position first; stay consistent with the philosophy (a trend follower cannot take profits whenever they occur); match the profile to the risk preference; plan for contingencies. | Principles. | 1029–1032 |
| C3 | **Liquidity cost**: `C = K × Q × V / (Lc × Lo)` (Ginter & Richie: cost rises with order size and volatility, falls with volume); K is larger when the order is in the direction of the price move; so transaction costs weigh most on systems that trade often, have small average profits and trade with the trend; choose the method with the fewest trades in the most liquid markets. | Slippage model. | 1033–1034 |
| C4 | **Measuring return and risk**: criteria — higher profits, order of profits and losses (consecutive vs alternating), no penalty for large gains (not only drawdown), shorter time to recovery, less time in market. **Sharpe/information ratio** satisfies only the first (cannot see order or surges); monthly data look better than daily because smoothed. **Treynor ratio** (beta). **Average Maximum Retracement** (Schwager): average drawdown ignoring new-high days. **Maximum drawdown and Calmar ratio** (`ARORt / MaxDD`): practical, but the future will have larger drawdowns. **Sortino** (downside deviation vs minimum acceptable return). **Ulcer Index** `sqrt(Σ D_i² / n)` where D is the percentage below the previous equity high. **Probability of a drawdown (DP)** = standard deviation of daily drawdowns (days with drawdown only) and **semivariance** around the regression line; **drawdown ratio** `ARORt / DPt` (satisfies all three criteria). Greater risk when: small sample, few historic equity drops, few product groups, compounding. | Which ratios to report. | 1034–1040 |
| C5 | **Annualised volatility** as risk and target-volatility basis; **VaR** (variance–covariance with correlations, historical, Monte Carlo; 1.65σ for 95%, 2.33σ for 99%; a worked example gives USD 17,068 for two positions instead of the sum of 11,650 + 12,475 because correlation is −0.27); returns can have kurtosis up to 25 (fat tails), so **stress tests** are required, treated as exceptions like crisis management; Hindenburg Omen (equity breadth; ~25% success; not applicable). | Portfolio-level risk estimates. | 1040–1044 |
| C6 | **Risk characteristics**: trend systems have many small losses and a few large wins, and cannot reduce the number of losing trades below a floor (sideways phases); **breakouts** exchange a larger risk per trade for higher reliability — **trade risk = max(High, n) − min(Low, n)**; compare systems after risk-adjusting returns (scale to the same risk); **time to recovery**; **stability of returns** (slope through annual returns: a decline means decay); "how much bigger could the risk be": 1% chance of a 50% loss per month is a 50% chance by the 50th month; with 100 cases there is a 10% error; **in a shock correlations go to 1** — "it's not the markets, it's the money". | Risk characterisation and caveats. | 1045–1046 |
| C7 | **Leverage**: margin multiplies P/L; practical leverage depends on the account size, not the margin; exchanges change margin slowly; broker margin call at 25% loss of initial margin. **Reserves and target volatility**: record daily P/L; standard deviation; choose target volatility (typically 15%; practical lowest 6–8%); required equity = annualised stdev of P/L ÷ target (example $266,592, 135× the average daily P/L); expect 2–2.5σ losses, so a 15% target implies a ~37% drawdown, aggressive; maximum risk level (liquidation) usually 50%, as low as 10%; exposure leverage vs risk-based leverage (regulators use face value). | Capital needed for a risk target. | 1046–1050 |
| C8 | **Position sizing**: equal money per stock gives unequal risk; three methods — (1) money ÷ price, (2) money ÷ (price × annualised volatility), (3) money ÷ (average true range × √252); results differ enormously (BAC: 62× the AAPL size in method 1, smallest in method 2, an ATR-based size in method 3); redistribute the money to match the available capital; ATR sizing reduced BAC equity volatility by 27% in a 200-day MA test; "equal risk gives each trade an equal chance to participate; unless you can select which trades are better, equal risk is the most conservative"; without size control portfolio volatility ranged 6%–25%; a rigorous test needs the investment defined as the largest amount needed. | Volatility-based sizing. | 1050–1054 |
| C9 | **Initial position risk**: trend systems accept small losses; breakouts' loss is the range (reducing it conflicts with the method); mean reversion takes large losses for high reliability, and stops reduce reliability. **Stops**: stop sized to the system, timing, volatility or chart pattern (not a fixed share of capital); options: parabolic, swing points, highest high/lowest low of n periods, KAMA, **3 × 10-day ATR**; **initial stop** at entry never moved; **trailing**: fixed percentage (3%), volatility-based (ATR/volatility; ISAM suggests 12 × ATR(252)), **percentage of profits** (50%, only after a trigger profit; use the closer of that and the initial stop); **Kase's Dev-stop** (ATR of 2-day true range + f × stdev, f = 1, 2.06–2.25, 3.20–3.50; applied from the trade extreme; triggered only on close). | Stop types. | 1054–1056 |
| C10 | **Profit targets**: essential in short-term trading (noise), harder in trend following (fat tail; need re-entry); `E + f × V` from the **system entry point, not the actual fill**; euro futures 60-minute test (80-bar and 5-bar MA, targets 0.5–10 × ATR(20), 2002–2010): the slow 80-bar system was best **without** profit-taking (net 121,655 vs 94,405 at a 10× target and falling with smaller targets) while the fast 5-bar system turned from −3,278 to +19,098 at 7.5×, and was otherwise negative for most factors; factors "usually arrived at by data mining"; **scaling out in three targets** reduces risk when target distance is uncertain. | Targets by style. | 1057–1059 |
| C11 | **Kaufman on stops**: stops and targets are a duel with noise; stops on close, targets on intraday spike; stops "work except when you need them most" (gaps, fills at the extreme); those most likely to work **adapt to volatility** and **trailing stops are more practical than initial stops**; heat map (30-year bonds 2000–2011, MA 10–100 × stdev-stop factor 2–10): nearly every stop average beat no-stop, but one market and period; **stop frequency vs distance**: with random data (number of hits) × (distance) is constant; **proximity risk** (clusters of stops, large trend programs taking up to 3 days to enter); **managing risk without stops**: reduce size as volatility rises (counting switching costs); **risk overlay** stops as % of margin or % of account (1–2.5%). | Stop evidence and alternatives. | 1059–1061 |
| C12 | **Market selection by noise**: `ER = |C_t − C_{t−n}| / Σ|C_i − C_{i−1}|` (n = 65); across futures and stocks 1990–2011, a 65-day MA system's profit factor tends to rise with the average ER (Eurodollar 0.1816 → 2.43; S&P 0.1203 → 1.16; MSFT, GE, wheat, soybeans, gold, MRK, IBM below or near 1.0); markets with low ER/profit factor below 1.0 suit mean reversion; "it is not necessary to include markets that conflict with the nature of the strategy". | Choose assets by noise. | 1070–1072 |
| C13 | **Probability of ruin**: equal-size wins/losses: `R = ((1 − A)/(1 + A))^c`, `A = P − (1 − P)`, c = capital in units (60% winners, c = 1 → 33%, c = 2 → 11%); with a goal G the formula changes; **unequal wins and losses** (Gehm): uses E (expected P/L per trade), E2 (expected squared P/L), `D = CA / E2`, `P = 0.5 + E / (2 √E2)`, `R = ((1 − P)/P)^D`; Vince derived similar results; needs enough trades and the history may understate risk. | Capital vs ruin. | 1072–1075 |
| C14 | **Equity trends and compounding**: increasing size with equity makes you fully invested at the top of the cycle; a +100%/−50% cycle yields nothing when compounded; alternative: hold exposure constant and let **reserves** accumulate, redistribute margin/reserves only after the drawdown stabilises. **Trading the equity curve** (stop trading when a 10- or 60-day moving average of the strategy's equity is falling; S&P and gold improved, bonds deteriorated; no switching costs; hypothetical equity is better than real): results inconsistent; check autocorrelation of returns first. | Dynamic sizing from equity. | 1085–1088 |
| C15 | **Optimal f**: `G(f) = P ln(1 + B f) + (1 − P) ln(1 − f)` (Kelly); `f = [p (PLR + 1) − 1] / PLR` (p = 0.5, PLR = 2 → 25%); with fractions of current equity three losses in a row cost 57.81%, not 75%; optimal f computed from history changes with every trade, overbetting leads to ruin, underbetting reduces profit geometrically; Elder's lessons (never average down, never meet margin calls, liquidate the worst first); drawdown inside a trade can far exceed the final result; Markowitz approximation: optimal leverage `= μ/σ²`; **"consider using these methods only to reduce leverage, not increase it"**. | Kelly/optimal f with caveats. | 1088–1092 |
| C16 | **Comparing expected and actual**: a 33% win rate and 4:1 payoff — should trading stop after 10 losers? Use the **binomial distribution** `B(l; p, n) = n!/(l!(n−l)!) p^l (1−p)^(n−l)` to compute the probability of l losses in n trades; the run formula `(1/2)^(n+2)`. (The conclusions and tables on pp. 1093–1098 were not read.) | Is the system broken? | 1092–1093 |

Crypto remarks below are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Per-trade risk cap | ✅ | `assess_signal` (risk_management/domain): position fraction cap, risk-per-trade computed from the stop distance, `max_candle_range_pct`, notional caps; live caps and kill switch. |
| Sizing from stop distance | ✅ (live) | Risk-per-trade ÷ stop distance; stop distance is a fixed percentage, hence not volatility-aware (ch. 20 O2). |
| Sizing in the backtest | ⚠️ | Trivial all-in sizing in the backtester differs from the risk module live → backtest does not reproduce risk-managed sizing (known gap). |
| Volatility targeting | ❌ | None. |
| Metrics: Sharpe, Sortino, Calmar, Ulcer, DP, drawdown ratio, recovery time | ❌ | `Metrics` has net PnL, return, buy&hold, max drawdown, fees, win rate, profit factor, avg trade PnL. |
| Stop types | ⚠️ | Fixed percentage stop and optional take profit; no trailing/ATR/dev stop; live uses exchange-native stops. |
| Profit-target semantics (from system entry price) | ✅ (by construction) | Targets computed from entry price (verify in `stops.py`). |
| Risk of ruin / Kelly | ❌ | None. |
| VaR | ❌ | One bot = one asset; no portfolio aggregation. |
| Market selection by noise | ❌ | No efficiency ratio. |
| Margin, leverage | n/a | Spot long-only; no margin or borrowing. |
| Trade the equity curve | ❌ | None. |
| Liquidity cost model | ❌ | Fixed `slippage_bps`. |
| Expected vs actual (binomial) | ❌ | None. |

## 3. Opportunities

### O1 — Extended risk metrics: Sortino, Calmar, Ulcer index, drawdown ratio, recovery time *(book: C4, pp. 1034–1040)*
Add (documented formulas, annualisation with 365 days for crypto): `Calmar = annualised return / max drawdown`, `Sortino` with an explicit MAR (default 0), `Ulcer Index`, **DP and drawdown ratio**, **longest drawdown duration and time to recovery**, **time in market**, and the Sharpe ratio with the caveat that it cannot see the order of returns or large surges. Report with the sample size (number of trades and number of days) and a warning when small (the book: few drawdowns, a small sample or short history means greater risk). Same family as ch. 2 O1/O2 and ch. 21 O7; implement once. **Complexity:** low. **Validation:** closed-form fixtures (monotone curves, a single drawdown); invariance to constant scaling of equity.

### O2 — Volatility-based position sizing in risk assessment and in the backtester *(book: C8, pp. 1050–1054)*
* **Proposal:** (a) in the risk module add a sizing mode `risk_per_trade / (k × ATR)` (the stop distance becomes the ATR multiple, ch. 20 O2) — "equal risk per trade"; (b) make the **backtester use the same sizing function as live trading** (closing the known gap) so that reported drawdown and return correspond to what the risk module would permit; (c) keep the all-in sizing as an explicit option for comparison.
* **Why:** the book's central sizing lesson is to equalise risk, not money (method 3, ATR-based, "considered the better measure"; reduced equity volatility by 27% in its BAC example). For a single-asset bot, volatility sizing means smaller positions in volatile regimes: the analogue of volatility stabilisation.
* **Caveats:** the book's own evidence is one stock and one strategy; volatility-scaled sizes change with time, so the investment needed is the largest ever needed; switching costs apply if sizes are rebalanced; fractional quantity and exchange minimums (lot size, `minNotional`) constrain small accounts.
* **Complexity:** medium (shared sizing function; backtest engine and tests). **Risks:** results of existing backtests change; keep the old mode as default behind an explicit parameter and version it in the result (reproducibility hash). **Validation:** identical outputs between backtest, paper and live sizing for the same inputs (property test); caps respected.

### O3 — Target-volatility sizing for the bot (research mode) *(book: C7, pp. 1048–1049)*
Compute from the backtest P/L series the capital required for a stated target annualised volatility (the book's table: `investment = annualised stdev of P/L / target`), and the implied expected 2–2.5σ drawdown (the book shows that a 15% target implies about a 37% drawdown). Provide as an **advisory calculator** next to the backtest ("with this P/L profile, 15% volatility needs X; a 2.5σ loss is Y% of it"); lowest practical targets of 6–8% as reference points. **Complexity:** low. Do not auto-resize live positions.

### O4 — Trailing stop family (percentage, ATR, percentage of profit with trigger) *(book: C9, C11, pp. 1054–1056, 1059)*
Same direction as ch. 19 O2 and ch. 20 O2: (a) fixed-percentage trailing from the highest close; (b) ATR trailing below the highest high; (c) **percentage-of-profit stop that activates only after a trigger profit**, using the closer of it and the initial stop; (d) optional **close-only** triggering (the book: stops on close exploit noise) — in crypto the close-based variant exposes to gap/flash risk between closes, so allow it only for backtest research or with the exchange-native stop remaining as a hard floor. Kaufman's view to carry: stops should adapt to volatility; trailing is more practical than the initial; use heat maps (ch. 21 O1) to judge; one market in the book. **Complexity:** medium (replace-order logic live). **Validation:** deterministic trail tests; parity backtest/paper.

### O5 — Do not use profit targets by default in trend strategies; offer scale-out as an experiment *(book: C10, pp. 1057–1059)*
The euro test shows profit-taking hurting the slow trend system and helping a very fast, noisy one. Document that default behaviour for `ema_crossover`/`donchian_breakout` is **no fixed targets** (they run until the exit signal), and let users compare with targets in the ablation tool (ch. 8 O7). **Scale-out** (three partial exits) could be an experimental risk setting; it needs partial-fill support in the position model (position, trades, and accounting by lot) — larger change, not recommended before the basics. **Complexity:** documentation now; high for scale-out.

### O6 — Stop-gap awareness: stops fail when needed most *(book: C11, p. 1060 · shock rules in ch. 22 O5)*
Keep the existing native exchange stop, and add a **gap-aware risk estimate**: report in the backtest the worst loss relative to the stop distance (stop slippage ratio), and size positions so the loss from a stop-through-gap (e.g. the largest observed candle gap or 5×ATR move) stays under the maximum acceptable loss. `max_candle_range_pct` partly addresses this for the signal candle only. **Complexity:** medium. **Validation:** synthetic gap fixtures.

### O7 — Efficiency-ratio view of assets and strategy suitability *(book: C12, pp. 1070–1072)*
Compute average ER over a window for each imported asset/timeframe and show it next to the strategy choice: low ER → noisy → trend strategies disfavoured; the book's scatter shows a positive trend of profit factor versus ER but with large exceptions (IBM, AMZN, gold) — it is a **guide, not a rule**. Combine with ch. 1 O1 (ER diagnostics), ch. 17 O2 (shared helper). **Complexity:** low. **Validation:** ER = 1 on a straight line; known fixtures.

### O8 — Risk-of-ruin and drawdown-probability advisory *(book: C13, pp. 1072–1075 · C16, p. 1092)*
Provide an advisory calculator using the platform's own trade statistics: (a) unequal win/loss risk of ruin (Gehm: E, E2, D, P, R) with a stated ruin threshold (e.g. a 50% drawdown) and a conservative reading — flag insufficient sample; (b) Monte Carlo of trade-order **bootstrap** (the book criticises block shuffling for trend strategies because it separates a profit run from its reversal; therefore present as one stress view, not as the risk estimate, and prefer a stationary/block bootstrap that preserves local structure — our addition, flag it as ours); (c) binomial expectation for consecutive losers (`P(l losses in n trades)`; for example the chance of 10 losses in the first 10 trades at a 67% loss rate = 0.67^10 ≈ 1.8%) to answer "should I stop the bot after k losses?" objectively. **Complexity:** low–medium. **Risks:** formulas assume independent trades with stable distribution; crypto has regime shifts, so label results "indicative". **Validation:** closed-form checks, simulation agreement within tolerance.

### O9 — Kelly/optimal f as advice only, with fraction *(book: C15, pp. 1088–1092)*
Show Kelly (`f = p − (1−p)/PLR` equivalent) and half-Kelly computed from the validated backtest statistics next to the configured position fraction, labelled "upper bound, not a recommendation". The book itself: use only to reduce leverage, never to increase; optimal f depends on the largest loss and changes with every trade; overbetting is the dangerous side. **Complexity:** low. **Risks:** users may treat it as a target; the UI must put it as a ceiling check ("your position fraction exceeds half-Kelly of the tested edge"). **Validation:** known examples (p = 0.5, PLR = 2 → 25%).

### O10 — Equity-curve filter as a research experiment, not a feature *(book: C14, pp. 1085–1088)*
Test "pause the bot when the moving average of its own equity is falling" in the backtester only; the book found inconsistent results (S&P and gold improved, bonds worsened) without switching costs, and warns that autocorrelation of returns must be checked first and hypothetical equity is optimistic. **H-EQUITY-FILTER**; run through the pipeline; **complexity:** medium; not recommended for live.

### O11 — Liquidity cost model calibrated from recorded fills *(book: C3, pp. 1033–1034)*
`cost ∝ order size × volatility / market volume` with direction-dependent factor (higher when buying into a rising price). Candles have volume; combine with ch. 16 O2 and ch. 20 O5 (volume cap). For small accounts the effect is negligible; the model matters when `capital` is scaled. **Complexity:** medium; calibrate only once enough fills exist.

### O12 — Reserve policy for compounding (informational) *(book: C14, p. 1085–1086)*
Document and simulate the three capital policies: full compounding, fixed size with accumulating reserve, and fixed size with redistribution after drawdown stabilises (the book's examples). A "capital policy" comparison in the backtester (position fraction applied to initial capital vs current equity) shows how compounding amplifies drawdowns. The platform's `position fraction` applies to current equity (verify). **Complexity:** low (parameterise the equity basis for sizing). **Validation:** deterministic examples from the book (+100%/−50% cycles).

### Not applicable
Futures margin, exchange and broker margin rules, European leverage limits, Hindenburg Omen, utility-curve theory (use only for the user's risk disclosure), VaR in the variance–covariance form for a multi-asset book (revisit when multiple positions are held at once, ch. 24), commercial hedgers, Treynor ratio (beta to the S&P).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 extended risk metrics | high | high | – | low | – |
| 2 | O2 volatility sizing + backtest/live parity | very high | very high | high | medium | ATR helper (ch. 20 O1) |
| 3 | O8 ruin/drawdown/binomial advisory | medium | high | – | low–medium | O1 |
| 4 | O9 Kelly ceiling check | – | high | – | low | O1 |
| 5 | O7 ER view | medium | – | – | low | ER helper |
| 6 | O3 target-volatility calculator | – | medium | – | low | O1 |
| 7 | O4 trailing stops | – | high | medium | medium | ATR helper; live design |
| 8 | O6 gap-aware sizing | – | high | – | medium | O2 |
| 9 | O12 capital policy comparison | medium | medium | – | low | engine |
| 10 | O5 no default targets / scale-out | – | medium | – | doc / high | – |
| 11 | O11 liquidity cost model | medium | – | – | medium | execution records |
| 12 | O10 equity filter | low | – | – | medium | pipeline |

## 5. Affected files
`analytics/domain/metrics.py` (and new analytics modules), `risk_management/domain/` (sizing modes, stops), `backtesting/domain/engine.py` (use the shared sizing function; capital policy), `trading/application/trader.py` (stop replacement), `execution/domain/fills.py` (cost model), `docs/openapi.json`, app backtest results and bot forms (advisory panels), tests.

## 6. Incremental plan
1. Metrics (O1), advisories (O8, O9, O3), ER view (O7) — read-only.
2. Shared sizing function and backtest parity (O2) behind an explicit option and a reproducibility version.
3. Trailing stops in backtest/paper (O4), gap-aware sizing (O6).
4. Capital policy comparison (O12); later experiments (O10, O11).

## 7. Acceptance criteria and tests
* All formulas match hand-computed fixtures (Calmar, Sortino, Ulcer, DP, ruin, Kelly examples from the book: p = 0.5, PLR = 2 → 0.25; ruin 60% winners c = 1 → 0.333, c = 2 → 0.111).
* Backtest and live sizing produce identical quantities for identical inputs; risk caps never exceeded; defaults unchanged.
* Advisories display sample size and carry "indicative only" labels; no live behaviour change.
* ruff, mypy, existing tests green.

## Caveats
Most numerical tables are futures or US equities, before modern crypto-specific costs; the book recommends 15% target volatility and 5%/3% per-trade limits as industry practice, not as proven optimum; VaR rests on normal returns while the book itself notes kurtosis up to 25; ruin formulas assume independent trades; optimal f's author-cited drawbacks are acknowledged in the text. The chapter's passages on averaging into positions, compounding by pyramiding, directional-movement market selection and the final expected-vs-actual tables were not read.
