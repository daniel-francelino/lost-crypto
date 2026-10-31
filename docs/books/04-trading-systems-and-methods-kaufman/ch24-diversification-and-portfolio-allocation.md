# Book 4 · Chapter 24 — Diversification and Portfolio Allocation

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 1099–1103 (introduction, diversification, multiple strategies) and 1115–1117 (portfolio theory for trading returns) were read. The section headings of the rest were seen (pp. 1103–1114: balanced risk, changing correlations, portfolio model types, classic allocation calculations, Excel Solver; pp. 1117–1146: objective function, constraints, the genetic-algorithm solution "GASP", optimal subsets, worked examples). Those parts were **not** read and are not summarised.

**Fit with the platform:** the system is one asset per bot, spot, long-only. A portfolio of several bots is possible (several bots running at once) but there is no portfolio-level view or allocator. This chapter therefore matters mostly for **future** multi-bot capital allocation and for correlation-aware risk, and is lower priority than chapters 20–23.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Diversification reduces **systematic** risk but not **market risk** (price shocks): "the subprime crisis proved that diversification can disappear under stress"; benefits are greatest when markets and decision methods are very different. | Limits of diversification. | 1099–1101 |
| C2 | **Select unrelated assets** (low covariance/correlation, check history and the forces currently driving the market); the "financials" (fixed income, currencies, indexes) are strongly interrelated; commodities react to the dollar and rates; long periods exist where each group follows its own fundamentals, but **in a shock all markets become highly correlated** ("money moves the market, not fundamentals"). With perfect independence risk would fall to 1/N (50%, 33%, 25%); in practice a fully diversified portfolio might reduce initial risk by only about 50%; the gain from adding assets falls quickly after about 4. | How many assets and which. | 1101–1102 |
| C3 | **Multiple strategies** also diversify, but methods that look different can be highly correlated (a moving average, ARIMA and point-and-figure are all trend following: they hold the same positions at some time); diversify by functional attribute: trend following vs countertrend/mean reversion, etc. | Strategy diversification. | 1102–1103 |
| C4 | **Allocating to trading returns, not prices**: classic mean-variance portfolio theory assumes a return every day; a strategy that is out of the market part of the time has zero-return days, so its standard deviation shrinks and it receives a **larger allocation although its risk when active is the same**; the covariance of intermittent returns is also distorted (two strategies in the market 50% of the time, together 25%; two strategies on the same market active 3% of days: the combined risk jumps when both are active though the statistic hides it); selective strategies with 10–20% time in market look poor (low beta, high deviation) yet offer high returns when active and real diversification. The author proposes a genetic-algorithm allocator (GASP) instead of mean-variance. | Pitfalls of optimising on strategy equity. | 1115–1117 |

Crypto remarks below are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Multiple bots running at once | ✅ | The system supports several bots; each is independent (own capital, own risk caps). |
| Portfolio-level view (aggregate exposure, correlation, drawdown) | ❌ | No portfolio module; the dashboard (app) shows per-bot data; live caps are per bot (verify whether a global cap exists in `risk_management`; the kill switch is global). |
| Correlation between bots/assets | ❌ | None. |
| Capital allocation across bots | ❌ | Manual; each bot has its own `capital` setting. |
| Strategy diversification measure | ❌ | None. |

## 3. Opportunities

### O1 — Portfolio view: aggregate exposure, drawdown, and cross-bot correlation (read-only) *(book: C1, C2, C3, pp. 1099–1103)*
* **Proposal:** a read-only analytics view over all running/paper/live bots that shows total capital in use, aggregate open exposure per asset (and **effective exposure when assets are correlated**), combined equity curve and drawdown, and the **correlation matrix of bot returns and of asset returns** over a rolling window (daily returns of **equity**, not of price: see C4), with a warning when correlation among held assets is high (crypto assets typically are, particularly in downturns: our observation to verify with data, not from the book).
* **Why:** the book's two lessons: unrelated assets reduce risk — "but in a shock correlations go to 1" — so the user must see the **concentration** that looks like diversification (several bots all long altcoins that follow BTC). **Complexity:** low–medium (analytics + endpoint + page). **Risks:** correlations are unstable and sample-dependent; show the window and sample size; no allocation recommendations. **Validation:** synthetic series with known correlation; handles bots with no positions (zero-return days) using the book's caution (C4): compute correlation also **only on days both are active** and display both versions.

### O2 — Global portfolio caps (design for approval) *(book: C1, C2 and ch. 23 C1)*
A global limit on the **sum of live exposure** and on **simultaneous correlated positions** (for example "no more than X% of total capital across assets in the same correlation cluster") in addition to per-bot caps. The existing global kill switch is a coarse version. This is a risk-policy change for a live-trading system and **must be decided with the user** before any code. **Complexity:** medium–high.

### O3 — Equal-risk allocation advisory (not an optimiser) *(book: C2 + ch. 23 C8, pp. 1050–1054)*
When the user runs multiple bots, an advisory could suggest relative capital using **inverse volatility (equal-risk) weights** (ch. 23 O2/O3) rather than equal dollars; the book's own sizing example shows that equal money concentrates risk in the most volatile asset. Present as information; do not auto-allocate. **Complexity:** low–medium. **Validation:** weights sum to 1; scale invariance.

### O4 — Do **not** build a mean-variance or genetic optimiser on bot equity now *(book: C4, pp. 1115–1117; remaining chapter not read)*
The author's argument is that mean-variance optimisation on intermittent trading returns misallocates (inactive strategies look safer). Beyond that, optimising allocations on historical returns is another layer of overfitting (book 3 ch. 6; book 4 ch. 21), with a very small number of independent strategies and short crypto history. Recommendation: **no allocator now**; if portfolio construction becomes a goal, first read pp. 1103–1146 and decide the objective (return ratio) and constraints with the user. **Complexity:** high.

### O5 — Strategy-diversification labelling *(book: C3, pp. 1102–1103)*
Tag each strategy in the catalog with its functional family (trend following, breakout, mean reversion, …) and show in the portfolio view how many families are active; both current strategies (`ema_crossover`, `donchian_breakout`) are trend following and therefore likely correlated. Supports the case for adding a mean-reversion family (books 1–2) as a diversifier — subject to its own validation. **Complexity:** low.

### Not applicable (this phase)
Excel Solver procedures, classic Markowitz formulas, GASP implementation, futures sectors and the dollar–commodity relations, optimal subsets of markets.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 portfolio view | – | high | – | low–medium | – |
| 2 | O5 family tagging | – | low | – | low | catalog |
| 3 | O3 equal-risk advisory | – | medium | – | low–medium | ch. 23 O2 |
| 4 | O2 global caps | – | high | high | medium–high | user decision |
| 5 | O4 optimiser | – | – | – | high | **not recommended now** |

## 5. Affected files
New read-only analytics (portfolio) plus an endpoint, `strategies/catalog.py` (family field), app portfolio page; for O2 `risk_management/domain` and `trading` only after approval; tests.

## 6. Incremental plan
1. O1 and O5 (read-only).
2. O3 advisory once volatility sizing exists.
3. Discuss O2 with the user; decide whether to read the rest of the chapter.

## 7. Acceptance criteria and tests
* Correlation and exposure aggregates match hand-computed fixtures; handling of inactive days is explicit and documented.
* No change in trading behaviour; ruff, mypy and existing tests green.

## Caveats
Only the introductory parts of the chapter were read; the author's claim that his genetic-algorithm allocator beats mean-variance rests on sections not read here. The diversification curve (≈50% maximum risk reduction) comes from the book's figure and futures/stocks data. For crypto, high cross-asset correlation is an expectation to verify with the platform's own data, not a finding.
