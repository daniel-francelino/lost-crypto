# Book 5 · Chapter 1 — Financial Machine Learning as a Distinct Subject

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 3–15 were read (motivation, why projects fail, book structure by production chain / component / pitfall, audience, FAQs up to the start of "econometrics"). Pp. 16–20 (remaining FAQs and the closing of the chapter) were not read. The chapter is organisational and methodological; it contains no algorithms. Its value is a map of pitfalls (Table 1.2) that the rest of the book addresses, plus a **strategy lifecycle** that matches the platform's paper/live gating.

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Motivation: bridge academia and industry; finance should serve a purpose; many investors will use off-the-shelf ML and lose money; **backtest overfitting** is the characteristic difficulty of financial ML; financial ML is a subject distinct from standard ML. | 3–4 |
| C2 | **Why projects fail — the Sisyphus paradigm**: every researcher alone produces either a false positive from an overfit backtest or standard factor investing. Cure: the **meta-strategy paradigm** (a research factory with specialised stations: data curators, feature analysts, strategists, backtesters, deployment team, portfolio oversight). Producing one true strategy costs almost as much as producing a hundred. | 4–5 |
| C3 | **Production chain details**: feature analysts' findings are libraries usable for execution/monitoring/market making, "a common error is to believe that feature analysts develop strategies"; **strategists** must formulate a theory identifying "the economic mechanism that causes an agent to lose money to us" (behavioural bias, asymmetric information, regulatory constraint) — "features may be discovered by a black box, but the strategy is developed in a white box"; **backtesters** must evaluate "the probability of backtest overfitting by taking into account the number of trials it took to distill the strategy" and **should not share results back** with research (to avoid feedback), reporting to management; the deployment team ensures the deployed solution is logically identical to the prototype. | 7–8 |
| C4 | **Strategy lifecycle** (portfolio oversight): (1) **embargo** — run on data after the backtest end date; (2) **paper trading** on a live feed (latencies, execution delays); (3) **graduation** to a real position with precise attribution; (4) **re-allocation** — allocation follows a concave path (small at graduation, increases while it performs as expected, shrinks as performance decays); (5) **decommission** when it underperforms for long enough to conclude the supporting theory no longer holds; release new variations in parallel. | 8–9 |
| C5 | **Structure by component (Table 1.1)** and **by pitfall (Table 1.2)**: Sisyphus paradigm → meta-strategy; research through backtesting → feature importance analysis; chronological sampling → volume clock (ch. 2); integer differentiation → fractional differentiation (ch. 5); fixed-time-horizon labelling → triple-barrier (ch. 3); learning side and size simultaneously → meta-labelling (ch. 3); weighting of non-IID samples → uniqueness weighting and sequential bootstrap (ch. 4); cross-validation leakage → purging and embargoing (ch. 7, 9); walk-forward (historical) backtesting → combinatorial purged cross-validation (ch. 12); backtest overfitting → synthetic-data backtests and the deflated Sharpe ratio (ch. 11–16). | 9–13 |
| C6 | Experimental mathematics: "solve hard problems by experiment"; use experimental methods (ch. 11–15) to assess a strategy more reliably than a single historical simulation; "**whatever you do, always ask yourself in what way you may be overfitting**"; "overfitting is unethical … when done knowingly, overfitting is outright scientific fraud"; the industry "only pays for out-of-sample returns"; each backtest is overfit to some extent and the amount must be quantified. | 11–12 |
| C7 | **Audience**: researchers with ML experience; code in Python (pandas, numpy, scikit-learn). FAQs: ML may help where decisions follow rules (execution, risk monitoring) and increasingly for judgement calls; machines comply with rules and keep logs; **meta-labelling lets an ML layer sit on top of a discretionary or rule-based side decision**; econometrics is mostly linear regression, which "does not learn". | 12–15 |

All numerical claims in the book that this chapter promises (e.g. the deflated Sharpe ratio, purging) are evaluated in later chapters; this chapter itself provides no empirical evidence.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Research process with stations and responsibilities | ⚠️ | A single developer; the platform has separate modules (market_data, strategies, backtesting, analytics, risk, trading) that mirror the stations at the code level, but no process or artefact separation (e.g. a "research log"). |
| Trials accounting ("number of trials to distil the strategy") | ❌ | No count of runs per strategy family; sweeps are capped by `MAX_SWEEP_RUNS` and not corrected (ch. 21 O2 of book 4). |
| Strategy hypothesis / economic mechanism metadata | ❌ | Strategies have a catalog description but no stated mechanism or expected profile (book 3, book 4 ch. 21/22). |
| Embargo period (data after the backtest end) | ❌ | The train/test split is internal to the same period; no "forward holdout" kept untouched (book 3 ch. 6 O5 / book 4 ch. 21 O3). |
| Paper trading before live | ✅ | Paper trading and a paper-days gate before live exist. |
| Graduation / re-allocation / decommission lifecycle | ⚠️ | States exist (draft, paper, live, stopped) but no automatic performance-vs-expectation reassessment, no decay-based reduction of allocation, no retirement rule. |
| Decoupling backtest feedback from research | ❌ | Results are visible to the user and iterated upon freely; no locked evaluation. |
| ML pipeline (features, labels, models) | ❌ | None. The platform is rule-based; see the later chapters for what an ML layer would need. |
| Reproducibility | ✅ | Seed and candle SHA-256 stored per backtest. |

## 3. Opportunities

### O1 — Strategy lifecycle states with evidence gates *(book: C4, pp. 8–9)*
* **Proposal:** formalise the promotion path already partly present: **research (backtest-only) → embargo check → paper → graduated live (small allocation) → re-allocation → decommission**, with each transition requiring evidence recorded in the database: (a) embargo: performance on data **after** the backtest's end date compared with the backtest within a tolerance; (b) paper: duration and number of trades reached the planned sample; (c) graduation: starts at a small `position fraction`; (d) re-allocation: increase/decrease based on live-vs-expected statistics; (e) decommission when performance is below expectation for a defined time (the book: "enough to conclude the supporting theory is no longer backed by empirical evidence").
* **Why:** matches the platform's safety philosophy (live disabled by default, paper gating) and gives the paper-days gate **content** (book 4 ch. 22 O2, ch. 21 O9). The concave allocation path (small, grow, shrink as it decays) is a natural risk rule for a retail account.
* **Complexity:** medium–high (state machine, evidence fields, UI); decisions about automatic vs manual promotions are the user's. **Risks:** over-engineering for one user; start with a checklist view only. **Validation:** transition tests; no live order can occur from a state that has not passed required gates.

### O2 — Embargo period: reserve forward data after the backtest end *(book: C4, p. 8)*
Add the concept of a **forward embargo**: when a strategy is validated on data up to date T, record T and later evaluate the same fixed configuration on the data accumulated after T (for paper trading it is automatically the live feed; for backtests it is the newer candles imported later). Report embargo performance vs backtest expectation. Without extra modelling this uses the existing data import and a stored "validated until" timestamp on the backtest/bot. **Complexity:** low–medium. **Validation:** the embargo evaluation uses only candles after T; configuration is immutable between validation and embargo.

### O3 — Hypothesis/mechanism field and trial counter on each strategy configuration *(book: C3, p. 7–8)*
A required text field "why should this make money (who loses to us)" for any bot promoted beyond backtest, and a **trial counter** attached to each strategy family (number of backtests/sweep runs, including discarded ones) shown beside reported results (inputs for the deflated Sharpe ratio, chapter 14). Same as book 4 ch. 21 O2. **Complexity:** low. **Risks:** the text is only an honesty aid.

### O4 — Treat backtest feedback as consumable: separate research and evaluation *(book: C3, p. 8)*
The book's backtester station does not share evaluation results with research because feeding results back creates selection bias (explained in ch. 11). Platform analogue: an **evaluation backtest** (locked data, run once per configuration family, result stored and not used to tune) distinct from **research backtests**. Same as book 3 ch. 6 O5 / book 4 ch. 21 O3. **Complexity:** medium.

### O5 — Roadmap use of the rest of the book
Map the pitfalls in Table 1.2 to potential platform work, in order of relevance to a rule-based, one-asset, long-only system: (1) backtest statistics, deflated Sharpe, trials accounting (ch. 14, 11), (2) purged/embargoed validation and combinatorial purged CV (ch. 7, 12) if any ML or parameter-learning is added, (3) triple-barrier labels and meta-labelling (ch. 3) as a way to add an ML filter **on top of** the existing rule-based signals without replacing them, (4) bet sizing from probabilities (ch. 10), (5) structural breaks and entropy features (ch. 17–18) as diagnostics, (6) volume/dollar bars (ch. 2), (7) fractional differentiation (ch. 5) only if features for models are built. Details are in the corresponding chapter reports.

### Not applicable
Organisational advice for teams of PhDs, high-performance computing and quantum algorithms (ch. 20–22; the platform is a single-user system), market microstructure data protocols (FIX) and multi-asset-class data curation.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O3 hypothesis + trial counter | high | – | – | low | – |
| 2 | O2 forward embargo evaluation | high | medium | – | low–medium | candle import |
| 3 | O4 research vs evaluation separation | high | – | – | medium | segments |
| 4 | O1 lifecycle gates | medium | high | high | medium–high | metrics, alerts |
| 5 | O5 roadmap | – | – | – | – | later chapters |

## 5. Affected files
`backtesting` (stored validation date, evaluation runs), `trading`/bot models (state machine and evidence), `analytics` (comparison of embargo vs backtest), app bot detail page (gates view), docs.

## 6. Incremental plan
1. Hypothesis and trial counter (metadata only).
2. Forward embargo report.
3. Locked evaluation run.
4. Lifecycle gates with user approval of each rule.

## 7. Acceptance criteria and tests
* Trial counter increments for every run and sweep member; embargo evaluation excludes data up to T; gates block transitions that lack evidence; defaults do not alter existing flows; ruff, mypy, existing tests green.

## Caveats
This chapter makes arguments by experience, with no data. The advice to separate research from backtesting and the meta-strategy paradigm is aimed at institutional teams; for a single user the equivalents are discipline and tooling that enforce it. The author's strong claims about the unethical nature of overfitting and about ML replacing discretionary investing are opinions, not results.
