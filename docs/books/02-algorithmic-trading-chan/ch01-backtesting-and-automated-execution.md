# Book 2 · Chapter 1 — Backtesting and Automated Execution

*Algorithmic Trading: Winning Strategies and Their Rationale*, Ernest P. Chan (Wiley, 2013). Book pages (PDF page = book page + 18). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

Reading note: pp. 1–38 were read. The software-platform survey (pp. 25–36: Deltix, Apama, MATLAB bridges, open-source IDEs, colocation, multithreading, CEP) describes products and was read for its principles only.

## 1. Chapter summary (pp. 1–38)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | **Backtest every strategy yourself**: results depend on implementation details (order type, price used to trigger); the same program should become the execution program. A published strategy gives a genuine out-of-sample period **after publication**. Follow the scientific method: hypothesis → backtest → refine. | Unreproducible or detail-sensitive claims. | 1–3 |
| C2 | **Look-ahead bias** is a programming error that can exist only in a backtest; if backtest and live are the *same program* fed different data, it cannot occur. | Future leakage. | 4 |
| C3 | **Data-snooping bias**: too many free parameters. Detect with out-of-sample data; but tweaking after a poor out-of-sample turns it into in-sample. Use **cross-validation** (several subsets); prefer high Sharpe and short maximum-drawdown duration because they pass cross-validation almost automatically. Few parameters **and few rules**; **linear models are less prone to snooping** than non-linear (a non-linear model has a linear approximation; justify not using it). Occam's razor also for distributions: assume Gaussian unless there is strong reason otherwise (author's argument). Equal-weight factor combination (z-scores or signed ranks) is cited as robust (Kahneman quote; Greenblatt's "magic formula" 30.8% vs 12.4% APR, 1988–2004 is the author's illustration). | Overfitting. | 4–7 |
| C4 | **Walk-forward test** is the final out-of-sample check: paper trading or, better, minimal-leverage live trading; **most traders would be happy to find live Sharpe better than half of backtest Sharpe** (author's experience). | Final validation. | 7 |
| C5 | **Data pitfalls**: splits/dividends (adjust history, also live); survivorship bias (hits long-only mean reversion most; momentum less; buy-the-biggest-loser example); **primary vs consolidated prices** (auction open/close vs away-venue prints; consolidated highs/lows are exaggerated; backtests with them inflate mean reversion); **venue dependence of currency quotes** (use data from the venue you trade; spreads differ by venue); **short-sale constraints** (hard-to-borrow, bans, uptick rules); **futures continuous contracts** (roll gaps create false P&L; price vs return back-adjustment cannot both be right; negative prices); **settlement vs last price**; **asynchronous prices in spreads**. | Inflated or unrealistic backtests. | 7–16 |
| C6 | **Statistical significance by hypothesis testing**: null hypothesis = true mean return is zero; test statistic = average daily return; p-value. Three ways to build the null distribution: (1) assume Gaussian: statistic = `mean/std × √n` (equivalently daily Sharpe × √n) with critical values 1.282 / 1.645 / 2.326 / 3.091 for p = 0.10 / 0.05 / 0.01 / 0.001; (2) **Monte Carlo** on simulated prices with the first four moments of the real series (the example: 1,166 of 10,000 simulations did as well, so only 88% confidence); (3) **random entry dates** with the same number of trades and holding period (Lo et al.; in the example 0 of 100,000 did as well). The three can disagree because each compares against a different notion of randomness. Critique: p-values give P(R | H0), not P(H0 | R). More round trips → higher significance. | "Is this backtest luck?" | 15–22 |
| C7 | **When not to backtest** (red flags): high return but Sharpe 0.3 with a 2-year drawdown; long-only strategy not beating buy-and-hold on the **information ratio**; "buy cheapest stocks" without survivorship-free data; neural net with ~100 nodes; high-frequency backtests whose results depend on how other participants react. | Wasted effort. | 22–24 |
| C8 | **Is a backtest predictive?** It assumes unchanging statistical properties; regime shifts (decimalisation 2001, 2008 crisis, Reg NMS 2007, uptick rule changes) can make pre-shift backtests worthless; recent data is no guarantee either. | Stationarity of the edge. | 24–25 |
| C9 | **Platform choice**: a platform where backtest and live are one program removes transcription errors and look-ahead; event-driven (tick) vs bar-driven; latency comes mostly from data and broker confirmation (retail confirmations can take seconds); colocating on a cloud server mainly gives resilience to power/Internet outages and may not reduce latency (verify with ping); multithreading; CEP; news feeds. | Operating the system. | 25–36 |
| C10 | Key points recap, including: walk-forward beats other snooping defences; simple models; verify with the right benchmark. | – | 37–38 |

Everything about equities, futures and currencies is equity-market specific. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| C1 same strategy code in backtest and live | ✅ | One `Strategy` class per type, used by `run_backtest` and by the trader; fill and stop logic are shared (`execution/domain/fills.py`, `risk_management/domain/stops.py`). The *engine loops* differ (`backtesting/domain/engine.py` vs `trading/application/trader.py`) and risk sizing exists only in live (chapter 5 of book 1). |
| C2 look-ahead | ✅ by design, ❌ not tested | Strategy sees only the closed candle; fill at next open. No automated truncation test (book 1, ch. 3 O5). |
| C3 cross-validation | ❌ | One fixed train/test split only (`segments.py`). |
| C3 simplicity | ✅ | ≤ 4 parameters per strategy. |
| C4 walk-forward / minimal-leverage live | ✅ partly | Paper stage mandatory (`live_min_paper_days`), live caps exist, but nothing compares live Sharpe to backtest Sharpe. |
| C5 venue consistency | ✅ | Candles come from the same exchange adapter that executes (`ExchangeRegistry.market_data(cfg.exchange)`); data is per exchange in storage. |
| C5 survivorship | ❌ | No delisting handling (book 1, ch. 3). |
| C5 splits/dividends/futures/shorting | n/a | Spot long-only crypto. |
| C5 consolidated-vs-primary analogue | n/a | Single venue. Aggregated "indices" are not used. |
| C6 significance tests | ❌ | None: no p-value, no Monte Carlo, no random-entry test, no Sharpe significance. |
| C6 number of round trips | ✅ | `round_trips` exposed, but not tied to confidence. |
| C7 red-flag screening | ❌ | No automated sanity flags on a run (low Sharpe with long drawdown, not beating buy-and-hold). `buy_and_hold_return_pct` exists. |
| C8 regime shifts | ❌ | None tracked; train/test is chronological (recent data held out), which partly helps. |
| C9 same program | ⚠️ | Same strategy; different orchestration. |
| C9 resilience / hosting | ⚠️ | See book 1, ch. 4 (continuity runbook). |
| C9 latency | ✅ | Bars are 1 min+; seconds-scale latency is irrelevant at these horizons. |

## 3. Opportunities

### O1 — Statistical significance of a backtest *(book: C6, pp. 15–22)*
* **Problem:** a positive backtest return is shown without any measure of whether it could be luck; sweeps worsen it.
* **Proposal (staged):**
  1. *Gaussian test statistic*: `daily Sharpe × √n` (n = number of return observations) compared with the book's critical values; report approximate p-value. Cheap, closed form.
  2. *Random-entry test*: re-place the same number of entries at random times with the same holding-period distribution over the actual price series and report the fraction of simulations whose average return is at least the observed; requires a deterministic seeded generator (the config already carries `seed`).
  3. *Monte Carlo on simulated prices* (matching four moments): defer; it needs a distribution generator (Pearson system) and heavy compute.
* **Benefit:** puts a number on "could be luck"; the book's own example shows the tests disagree, so they must be shown with their definitions. **Complexity:** stage 1 low; stage 2 medium. **Risks:** returns are serially correlated and fat-tailed in crypto, so the Gaussian shortcut is optimistic; many tests across a sweep inflate false positives (multiple testing, addressed in later books); a p-value is not the probability the strategy works (the book says so, p. 22). **Validation:** known synthetic series with and without edge; reproduce the book's critical values; seeded determinism.

### O2 — Walk-forward and cross-validation harness *(book: C3, C4, pp. 4–7)*
* **Proposal:** extend the single split to *k* chronological folds (for a trend strategy, parameters chosen on the earlier window, scored on the next) and report the dispersion of results across folds. Cross-validation across time should not shuffle data. Ties to book 1 ch. 3 O8 (backlog B-WALK-FORWARD) and to book 5 (purged cross-validation) which treats leakage between folds properly; **do not implement until book 5 is analysed.**
* **Complexity:** high.

### O3 — Run screening flags *(book: C7, pp. 22–24)*
* **Proposal:** a "red flags" block on each backtest: Sharpe below a threshold with long drawdown duration; return not above buy-and-hold (information-ratio style, using the existing benchmark); too few round trips for significance; high parameter count relative to sample (book 1 ch. 3 O6). Display as warnings, never as blocks. **Complexity:** low once Sharpe and drawdown duration exist. **Validation:** unit tests per flag. Thresholds are the author's examples, make them configurable.

### O4 — Live-vs-backtest Sharpe monitor *(book: C4, p. 7)*
* **Proposal:** for a bot with enough live/paper history, compute realised Sharpe on its equity snapshots and compare it with its backtest Sharpe; show the ratio and a note that the author considers ≥ 0.5 acceptable (his experience, not a standard). **Complexity:** low–medium. **Risks:** short live samples are noisy; show sample size. **Depends on:** Sharpe metric (book 1 ch. 2 O1) and parity report (book 1 ch. 5 O1).

### O5 — Honest out-of-sample bookkeeping *(book: C1, C3, pp. 3–4 · adaptation)*
* **Problem:** repeatedly editing parameters after looking at the test segment turns it into training data (the book's central warning).
* **Proposal:** record in each run which segment(s) the operator inspected when choosing parameters and count how many runs share the same data window; warn when the test segment has been used many times. Pragmatic version: number of runs on the same pair/timeframe/window shown beside the result. **Complexity:** low. **Validation:** API test.

### O6 — Information ratio against the right benchmark *(book: C7, p. 22–23)*
* **Proposal:** for long-only strategies compute excess returns versus buy-and-hold of the same pair and report their information ratio (book 1 ch. 2 gives the formula). Already partly in place via `buy_and_hold_return_pct`. **Complexity:** low.

### Not applicable / deferred
Splits/dividends, primary vs consolidated, currency venue dependence, short-sale rules, futures continuous contracts, settlement prices, platform selection (we already own our platform), CEP, news feeds, multithreading, colocation for latency. Colocation for **resilience** is covered by book 1 ch. 4.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O6 information ratio | medium | – | – | low | book 1 ch. 2 O1 |
| 2 | O3 red-flag screening | high | medium | – | low | Sharpe, DD duration |
| 3 | O1 stage 1 Gaussian significance | high | – | – | low | Sharpe |
| 4 | O5 test-segment reuse counter | medium | – | – | low | – |
| 5 | O1 stage 2 random-entry test | high | – | – | medium | O1 stage 1 |
| 6 | O4 live-vs-backtest monitor | – | medium | medium | low–med | parity report |
| 7 | O2 walk-forward / CV | high | – | – | high | book 5 |

## 5. Affected files
`analytics/domain/` (significance functions, information ratio), `backtesting/application/service.py` and `router.py` (additive result fields, run counters), `backtesting/domain/` (random-entry simulation, seeded), tests in `api/tests/unit`, `docs/openapi.json`, app backtest detail page.

## 6. Incremental plan
1. Metrics prerequisites from book 1 ch. 2 (Sharpe, drawdown duration).
2. Information ratio and Gaussian significance as additive fields.
3. Red flags block.
4. Random-entry test with seed.
5. Reuse counter; live-vs-backtest monitor.
6. Walk-forward after analysing book 5.

## 7. Acceptance criteria and tests
* The critical values reproduce Table 1.1; a series with injected edge has small p, pure noise does not.
* Random-entry test is deterministic for a fixed seed and its runtime is bounded.
* Old runs without new fields still render; ruff, mypy and existing tests green.
* UI wording states that a p-value is not a guarantee.

## Caveats
All thresholds (critical values excepted) are Chan's practical heuristics. The Monte Carlo and random-entry examples are for one futures momentum strategy and do not generalise. Statistical significance of a backtest says nothing certain about future returns; regime shifts can nullify it (p. 24).
