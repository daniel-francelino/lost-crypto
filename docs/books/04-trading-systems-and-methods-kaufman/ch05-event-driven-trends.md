# Book 4 · Chapter 5 — Event-Driven Trends

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 181–184 (swing trading definition and the start of the swing-chart construction) and pp. 222–233 (**N-day breakout, Donchian rules, Turtles**) were read in full. The remainder of the swing-filter construction (pp. 184–194) and **point-and-figure charting (pp. 195–221)** were **not** read and are not summarised. This report is mostly about the N-day breakout, the section closest to the project's `donchian_breakout`.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Event-driven trend methods ignore elapsed time** and react to price reaching a new extreme: a new high or low "means something important has changed". The author asks the reader to keep asking whether newer, more complex methods improved on these simple ones. **Swing trading**: a swing is a sustained move larger than a threshold (the *swing filter*, in absolute units or percent of price); a swing chart has no time axis; classic construction in seven steps with an outside-day convention that must be applied consistently. | Simplest objective trend definition. | 181–184 |
| C2 | **N-day breakout**: buy when today's high exceeds the highest high of the past N days; sell when the low falls below the past N lows (always in the market, reversing); a more conservative form uses **closes** for confirmation, entering later. N below ~5 days is not event-driven but trend continuation. The **risk** of a breakout position is the distance from entry to the opposite N-day extreme: **larger N → much larger risk per trade**. Compare with time-based moving averages in ch. 8. | Basic trend system and its risk profile. | 222–223 |
| C3 | **Donchian's 4-week rule** (entry above the previous four weeks' highs, with symmetric short rule): long-lived "slow breakout"; the key to success and the problem for risk control is that the channel scales with each market's volatility so **volatile markets overwhelm quiet ones**; modern practice sizes positions to keep **risk constant**, which corrects the biggest problem of event-driven strategies. | Position sizing for breakouts. | 223–224 |
| C4 | **Choosing N**: backtesting a range is the obvious approach; also proposed: **`N_t = N_I × V_n / V_c`** (normal vs current volatility; N shrinks as volatility rises, an adaptive technique). | Fixed vs adaptive N. | 224–225 |
| C5 | **Testing the N-day rule** (crude oil, N from 10 to 100 in steps of 5, 1991–2010, no costs, back-adjusted futures): only **one test lost money**; the pattern differs between 1991–2000 and 2001–2010; **best N by net profit: 75, 15 and 100** for the first decade, the second and the combined period respectively. Table 5.7 (2001–2010, futures and stocks): best N jumps from **10 to 95** across markets, and the share of profitable N values ("robustness") ranges from about 21% to 100%; percent profitable trades 31%–48%. | N is unstable across markets and periods. | 225–227 |
| C6 | **Weekly breakout**: act on Friday closes only; about 75% of the futures in a 1982 study showed higher risk than crossover systems; implement on weekly bars rather than from daily data (weeks that end on Thursday break day-of-week logic). | Lower frequency channel. | 225–228 |
| C7 | **Dynamic Breakout System** (Stridsman): anticipate the next day's entry and exit levels from a multiple of the standard deviation and place stop orders ahead; analyse the time-to-stop distribution (quick failures versus long holds) to place stops better. | Order placement for breakouts. | 228 |
| C8 | **Futures vs stocks**: futures are leveraged and commissions are tiny relative to face value (about 0.7 bp for an E-mini), stocks cost about 3 bp per round of a fixed $9; **returns must be judged per unit (cents per share, dollars per contract)** to see whether commissions and slippage are covered. | Cost realism. | 228–229 |
| C9 | **Donchian's 40/20** (earliest recorded N-day breakout: long entry channel for entries, short channel for exits) and **the Turtles' system**: S1 enter at the 20-day breakout, exit at the 10-day opposite extreme, with a **filter** that skips an entry if the previous S1 trade was profitable; S2 55/20 without the filter; **risk control**: stop at 2L from entry where `L` is the 20-day average true range in dollars; unit size equalises `L × big-point value` across markets (**1 unit = 1% of equity / (L × BPV)**), position limits by correlation group (4/6/10/12 units), pyramiding one unit for each move of L up to 5 units with stops raised to 2L, **portfolio risk management**: cut position size by 20% for every 10% drawdown from the peak and add 10% back per recovery step. The faster S1 on copper showed profits only in the first part of the 1980s; the slower S2 steady profits across 30 years; plain N-day breakout on copper 1980–2010 was profitable for all but one N, and "55 and 20 were not the best". | A complete rule set with sizing and risk. | 229–233 |

Examples are futures and stocks, long and short, with leverage. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| N-day breakout with separate exit channel (40/20, 20/10, 55/20 form) | ✅ | `donchian_breakout`: `entry_period` default 20, `exit_period` default 10 (the Turtle S1), long-only, based on **closes versus previous channels** (more conservative variant). |
| Risk per trade grows with N; sizing to constant risk | ⚠️ | `RiskLimits.max_risk_per_trade_pct` sizes from the stop-loss; but the Donchian strategy's stop is optional and a percentage, **not** tied to the channel or to ATR; with no stop, risk = entry to exit-channel low is unbounded by sizing. |
| ATR (`L`) based stop and sizing | ❌ | No ATR helper or ATR-based stop (also book 4 ch. 4 O3). |
| Volatility-adaptive N | ❌ | None (see ch. 17). |
| Robustness measure "share of N values profitable" | ❌ | Sweeps give a grid of results but do not report the share of profitable cells or a neighbourhood stability measure (book 1 ch. 3 O7, book 3 ch. 6 O4). |
| Instability of best N across periods | ❌ | Not reported: no comparison of the best N in different sub-periods. |
| Turtle filter (skip after a profitable trade) | ❌ | None. |
| Pyramiding (add units on favourable moves) | ❌ | One entry per position (the engine rejects BUY while in position). |
| Drawdown-based size reduction (−20% per 10% drawdown, restore on recovery) | ❌ | Bots pause at `max_drawdown_pct`; no graduated reduction (book 1 ch. 6 O3, book 2 ch. 8 O2). |
| Correlation-group position limits | ⚠️ | Global `max_open_positions` and `max_total_exposure`; no correlation groups. |
| Costs per unit (cents per share) | ✅ | Fee in rate and slippage in bps on notional; evaluated per fill. |

## 3. Opportunities

### O1 — Robustness summary of a one-parameter sweep: share of profitable values and best-N stability *(book: C5, pp. 225–227)*
* **Problem:** a sweep over `entry_period` is read as "pick the best N", which the book shows is unstable (75, 15, 100 for the same market; 10 to 95 across markets).
* **Proposal:** for sweeps over a single parameter, report (a) the share of grid values with positive net return after costs, (b) the best value in each sub-period (first half / second half) and the **rank correlation** between sub-period profit curves, (c) a smoothness measure (how much a cell differs from its neighbours). Show a "stable plateau" vs "isolated spike" indicator. Extends the neighbourhood-robustness idea in book 3 ch. 6 and book 1 ch. 3 C10. **Complexity:** low–medium (computations on stored run results). **Risks:** small samples; more slicing → multiple testing; still no guarantee. **Validation:** synthetic profit curves (plateau vs spike).

### O2 — Channel-aware risk sizing for the Donchian strategy *(book: C2, C3, C9, pp. 222–224, 230–231)*
* **Problem:** the strategy's risk per trade is the distance to the exit channel low, which varies widely; the book calls constant-risk sizing the key correction for breakouts, and the Turtles use `1 unit = 1% / (ATR × value)`.
* **Proposal:** let the strategy propose its **initial stop at the exit-channel low** (or at `k × ATR` below entry) as a protective level on the entry signal; the existing `max_risk_per_trade_pct` machinery in `assess_signal` then sizes the position so that being stopped costs a fixed share of equity (this machinery exists but only works when the signal carries a stop). Offer an ATR-based stop as an option. This reuses the live sizing code; the backtester does not use it (book 1 ch. 5 O2).
* **Benefit:** constant risk per trade, avoiding the dominance of high-volatility periods. **Complexity:** low–medium (ATR helper, signal change, parameter, app form). **Risks:** stop at the channel low is a *level the strategy would exit at anyway* (the exit rule), so the stop only matters for gaps/intrabar moves and for sizing; a real exchange stop order at that level places a visible order; interaction with backtest all-in sizing (needs O2 of book 1 ch. 5 to see the effect). **Validation:** unit tests that sizing equals `risk% × equity / (entry − stop)`; backtest with risk-aware mode.

### O3 — Volatility-adaptive N as an option *(book: C4, pp. 224–225)*
Define `N_t = N_I × V_n / V_c` with explicit `V_n` and `V_c` windows. Discussed again with the adaptive techniques of ch. 17; do not build before the robustness view (O1) can show whether adaptive N is more stable than fixed N. **Complexity:** low–medium; adds parameters (windows). Hypothesis **H-ADAPTIVE-N**.

### O4 — Trade-level "filter after a winner" rule as an experiment *(book: C9, p. 230)*
The Turtle S1 filter (skip the next entry if the last one was profitable) is a documented rule with an economic story (don't re-enter just after a successful breakout run). Test as a boolean parameter through the pipeline; no expectation. Hypothesis **H-TURTLE-FILTER**. **Complexity:** low (state in strategy).

### O5 — Pyramiding and graduated drawdown reduction: backlog *(book: C9, pp. 230–231)*
Both need a position model with several units (B-TRANCHES / B-SCALE-IN, see book 2 ch. 3 and 6) and are documented together with book 1 ch. 6 O3. Record as **B-PYRAMID**. The Turtle portfolio rule (reduce size by 20% per 10% drawdown, add back 10% per recovery step) is a concrete, simple form of "gradual de-risking" to evaluate in book 1 ch. 6 O3. **Complexity:** medium–high.

### O6 — Report returns per unit and cost coverage *(book: C8, p. 229)*
Show for each backtest the average net profit per trade as a number of **basis points of notional** and the ratio to round-trip cost, so users can see whether costs are comfortably covered (profit per trade ≫ round-trip cost). Part of the metrics set (ch. 2 O1). **Complexity:** very low.

### Not applicable
Point-and-figure charting (not read), swing chart construction details, weekly Friday rule (crypto has no weekend closure; a weekly timeframe could be tested but not in the current `Timeframe` set), futures roll-forward rules.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O6 per-trade bps vs cost | medium | – | – | very low | metrics |
| 2 | O1 sweep robustness summary | **high** | – | – | low–medium | sweeps |
| 3 | O2 channel/ATR stop + sizing | – | **high** | – | low–medium | ATR helper, book 1 ch. 5 O2 |
| 4 | O4 Turtle filter experiment | low | – | – | low | pipeline |
| 5 | O3 adaptive N | low | – | – | low–medium | O1 |
| 6 | O5 pyramiding / drawdown scaling | – | medium | – | medium–high | position model |

## 5. Affected files
`strategies/domain/donchian_breakout.py` (stop proposal, filter), new ATR helper, `risk_management/domain/models.py` (already supports risk-per-trade sizing), `backtesting/application/service.py` (sweep robustness summary), `analytics/domain/`, app sweep and strategy forms, tests (truncation test for any new rule).

## 6. Incremental plan
1. Cost-coverage metric.
2. Sweep robustness summary.
3. ATR helper; optional stop proposal in Donchian; tests for sizing.
4. Experiments (filter, adaptive N) through the pipeline.

## 7. Acceptance criteria and tests
* Robustness summary reproduces known plateau/spike synthetic cases.
* Stop proposal respects the risk module's checks (`stop-loss must be below the entry price`) and leaves the default behaviour unchanged.
* ruff, mypy and all existing tests green.

## Caveats
All figures (best N values, profitable-test shares, Turtle rule performance) are for pre-cost futures tests, many with the author noting that the results are only illustrations. Cumulative charts for one market (copper) are not evidence of a general pattern. Nothing implies a breakout works on crypto spot.
