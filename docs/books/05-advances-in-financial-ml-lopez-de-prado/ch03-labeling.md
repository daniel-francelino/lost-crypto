# Book 5 · Chapter 3 — Labeling

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 43–54 were read (fixed-horizon labelling, dynamic thresholds, triple-barrier, side and size, meta-labeling, how to use it, quantamental, dropping labels start). The exercises and the code of `dropLabels` details were not read; snippets were skimmed.

**Why this chapter matters for the platform:** the platform's trade logic is already a **triple-barrier structure** (stop-loss, take-profit, plus an exit signal that works as a vertical barrier). Meta-labeling is the book's way to add an ML layer **on top of** an existing rule-based strategy (such as `ema_crossover`), so it is the most directly applicable idea in the book.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Supervised learning needs labels `y` attached to feature rows `X`. The **fixed-time horizon method** labels `y_i ∈ {−1, 0, 1}` from the return over `h` bars versus a threshold `τ`. Avoid it: (1) time bars have poor statistical properties (ch. 2); (2) one `τ` for all volatility regimes gives mostly zeros in quiet periods (example: τ = 1% when bar volatility ranges from 0.01% to 1%); (3) it **ignores the price path**: real strategies are stopped out, margin-called, or limited; "it is simply unrealistic to build a strategy that profits from positions that would have been stopped out". | Poor labels. | 43–44 |
| C2 | **Dynamic thresholds**: set profit-taking and stop-loss widths as a function of estimated volatility, e.g. a rolling exponentially weighted standard deviation of returns (Snippet 3.1, span in days). | Barriers scaled to risk. | 44 |
| C3 | **Triple-barrier method**: two horizontal barriers (profit-taking, stop-loss, widths = factor × volatility target) and one vertical barrier (maximum holding time in bars). The label comes from the **first barrier touched**: +1 upper, −1 lower, vertical: the sign of the return (or 0). It is **path-dependent**. Eight configurations `[pt, sl, t1]`: `[1,1,1]` standard; `[0,1,1]`; `[1,1,0]`; `[0,0,1]` = fixed horizon; `[1,0,1]`; `[1,0,0]`; `[0,1,0]`; `[0,0,0]` invalid. The horizontal barriers need not be symmetric. Computation: up to `I × h` conditions (10⁹ for I = 1e6, h = 1e3), hence parallelism. | Path-aware labels. | 45–47 |
| C4 | **Learning side and size**: when there is no model giving the side, barriers must be symmetric (or absent) because profit-taking vs stop-loss cannot be distinguished without a side. `getEvents` finds first-touch times for event timestamps (from ch. 2 sampling), with a minimum return filter `minRet`; the vertical barrier can be defined as the next bar after `numDays`. | Side-and-size labelling. | 48–49 |
| C5 | **Meta-labeling**: when a primary model (any: rule, econometric, discretionary) already decides the **side**, train a **secondary binary model** that decides whether to act (1) or pass (0) — i.e. the size, including zero; labels come from **PnL given the side** (asymmetric barriers are allowed). The secondary model's probability can size the bet. Binary-label values are `{0, 1}` instead of `{−1, 0, 1}`. | Learning the bet size on top of a known side. | 50–51 |
| C6 | **How to use it**: confusion matrix, precision/recall, F1 (harmonic mean). Use a primary model with **high recall** (even with low precision), then let the meta-model filter false positives to raise F1. Four additional reasons: (1) turns a white-box model into an ML system; (2) **limits overfitting**, since ML does not choose the side; (3) separate long and short meta-models with different features; (4) "achieving high accuracy on small bets and low accuracy on large bets will ruin you" — sizing is as important as selection. The book claims, from experience, that meta-labeling models "can deliver more robust and reliable outcomes than standard labeling models" (no data shown). | Why meta-labeling works. | 51–53 |
| C7 | **Quantamental way**: add meta-labeling on top of discretionary or technical calls; features could include market state, structural-break status (ch. 17), even the decision-maker's state (speculative). | Combining rules/humans with ML. | 53–54 |
| C8 | **Dropping rare labels**: some classifiers perform badly with imbalanced classes; recursively remove observations whose class is rarer than `minPct` (unless two classes remain). | Class imbalance. | 54 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Triple-barrier structure in trading | ✅ | The engine and risk module use a stop-loss (percentage), optional take-profit, and the strategy's exit signal; stops are checked on low/high with gap-through-open rule (`engine.py`, `risk_management/domain/stops.py`). No maximum-holding barrier. |
| Volatility-scaled barriers | ❌ | Fixed percentages (ch. 20 O2, book 4). |
| Path-dependent trade labelling for analysis | ❌ | Trades are recorded but no per-signal "what happened next" table (MFE/MAE, time to first touch of ±x·σ). |
| Features / labels / ML model | ❌ | No such module. |
| A primary model with known side | ✅ | Each strategy emits buy/sell/hold; long-only means the side is fixed (long) — the meta-labeling setting. |
| Signal records available for a dataset | ⚠️ | Backtests produce trades (entry/exit); signals that were rejected by risk (`rejected_signals`) are counted but not stored with features. |

## 3. Opportunities

### O1 — Signal outcome table with triple-barrier outcomes (no ML yet) *(book: C3, C4, pp. 45–49)*
* **Proposal:** for every entry signal generated by a strategy over a historical dataset (including those a position-state or risk rule would have skipped), compute the outcome under a configurable triple barrier: upper `k_up × σ_t`, lower `k_dn × σ_t` (σ from a rolling EWM volatility of returns, available as the shared helper from book 4 ch. 20 O1) and a vertical barrier of `h` bars; store first-touch time, which barrier, return, MFE/MAE. Display as a table and summary: share of upper/lower/vertical hits, expected return per signal, time to touch.
* **Why:** (a) shows whether a signal has edge **independent of the particular exit rule**, which is a cleaner test than the realised trade P/L of a path-dependent exit; (b) it is the dataset for meta-labeling and for stop/target design (MAE distribution answers "how tight can the stop be before it kills winners"; book 4 ch. 21/23); (c) it detects the labelling flaws the book criticises (fixed threshold, no path). 
* **Complexity:** medium (vectorised computation; storage for large histories). **Risks:** overlapping outcomes (chapter 4 addresses the dependence: consecutive signals share price paths, so counts overstate independent evidence); `h` and multipliers are parameters; the vertical-barrier label choice (sign vs 0). **Validation:** synthetic paths with known first touches (upper first, lower first, vertical); handles gaps through barriers (use open price rule consistent with the engine); no look-ahead (σ uses data up to the event bar).

### O2 — Align the engine's barriers with the triple-barrier vocabulary: add a maximum-holding (vertical) exit and volatility-scaled stop/target *(book: C2, C3, pp. 44–46)*
Add optional `max_holding_bars` to the risk config (exit at the next open after the vertical barrier is reached, equivalent to the book's vertical barrier) and, with the ATR/σ helper, volatility-scaled stop and target (ch. 20 O2 of book 4). Both stay off by default. This makes the live trading rules identical in form to the labelling rules, so anything learned from O1 transfers to execution. **Complexity:** medium (engine, paper venue, live trader with time-based exit). **Risks:** more parameters; the time exit differs from exchange-native stops (needs the bot's scheduler to place a market sell — already part of exit handling). **Validation:** deterministic exit at barrier; parity backtest/paper.

### O3 — Meta-labeling filter for the existing strategies (research prototype; requires approval) *(book: C5, C6, pp. 50–53)*
* **Proposal (design only):** keep `ema_crossover`/`donchian_breakout` as the primary (side = long), label each past signal with the triple-barrier outcome converted to `{0, 1}` (1 if the PnL given the side is positive), train a secondary classifier on features known at signal time (recent volatility, trend slope and strength, ER/noise, volume ratios, time of day, distance from channel, prior-trade outcomes), and use its probability to **filter** signals (act when above a threshold) and optionally **scale the position fraction** (never above the existing risk caps).
* **Why:** it fits the platform: long-only, one-asset, rule-based primary with high recall; the secondary model can only reduce or scale exposure, not invent trades, which limits damage from overfitting (the book's second reason). The book's claim of higher F1 and robustness comes from experience; no empirical table in these pages.
* **Prerequisites (must exist first):** labels from O1; purged/embargoed cross-validation and sample weights (ch. 4, 7), because overlapping labels leak information (book ch. 4/7); evaluation of the whole system, not classification metrics, by the backtest pipeline with trials accounting, deflated Sharpe (ch. 14) and a locked final segment; model persistence/versioning with data hash; inference inside the trader at signal time with exactly the same feature code as training (no train/serve skew); fallback to the unfiltered primary when the model is unavailable.
* **Costs/risks:** (1) crypto's small number of independent signals per asset (a few hundred trades) makes classifiers overfit easily; (2) regime shifts; (3) feature leakage; (4) complexity and maintenance; (5) a new dependency (scikit-learn, etc.) in a Python 3.12 project; (6) live decisions made by a model must be explainable and logged. **Complexity:** high. **Recommendation:** do the prerequisites (O1, chapters 4, 7, 14 items) first; treat O3 as a later research track and decide with the user.

### O4 — Evaluate filters with precision/recall *and* P/L, expose a confusion-matrix style report for signal rules *(book: C6, pp. 51–53)*
Even without ML, any **filter** applied to a primary signal (volatility, trend strength, time-of-day) can be assessed as a classifier on O1 outcomes: how many of the winners it keeps (recall), how many of the kept signals win (precision), and the P/L effect. This is the objective, simple version of the book 4 ch. 20 "eliminate or delay" and the "paired sweep" (book 4 ch. 22 O3). **Complexity:** low (after O1). **Validation:** fixtures with known TP/FP/FN.

### O5 — Rare-label handling and class balance checks (when ML arrives) *(book: C8, p. 54)*
Record class balance of labels per dataset and warn if a class is below a threshold; do not drop labels silently. **Complexity:** low; part of O3 when it exists.

### Not applicable
Fixed-time-horizon labels for model training (avoid), side-learning with symmetric barriers (we already have a known side), biometric/psychological features for discretionary traders, multiprocessing helpers (ch. 20 of the book).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 signal outcome table (triple barrier) | very high | high | – | medium | σ helper (book 4 ch. 20 O1) |
| 2 | O4 filter evaluation by precision/recall | high | – | – | low | O1 |
| 3 | O2 vertical barrier + volatility-scaled barriers in engine | medium | high | medium | medium | σ/ATR helper |
| 4 | O5 label balance checks | low | – | – | low | O1 |
| 5 | O3 meta-labeling filter | potentially high | medium | – | high | O1, ch. 4, 7, 14 |

## 5. Affected files
`analytics/domain/` (outcome computation), `backtesting/application` (signal dataset generation, endpoint), `risk_management/domain` and `backtesting/domain/engine.py` (barrier options), `trading` (time exit), `docs/openapi.json`, app (signal outcome view), tests; an `ml/` module only after approval of O3.

## 6. Incremental plan
1. σ helper; outcome table (O1) with tests; summary view.
2. Filter evaluation (O4).
3. Barrier options in engine/paper (O2).
4. Revisit meta-labeling (O3) after chapters 4, 7 and 14 are implemented.

## 7. Acceptance criteria and tests
* Outcome table: each synthetic path yields the expected first-touch label and time; gap-through-barrier handled per engine rules; no look-ahead; outputs deterministic with the dataset hash.
* Barrier options: off by default and identical to existing results; on, they trigger exits on the correct bar; parity between backtest and paper.
* ruff, mypy, existing tests green.

## Caveats
The book states that the triple-barrier method and meta-labeling are its own inventions and that they do not exist in the literature; the claims of robustness are asserted from experience (no experiment in these pages). The barrier method labels signal quality, not profitability after costs; costs and slippage must be included in label returns for a realistic target. With few signals per asset, the benefit of any classifier is doubtful.
