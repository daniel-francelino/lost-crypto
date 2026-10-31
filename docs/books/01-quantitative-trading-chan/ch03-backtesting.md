# Book 1 · Chapter 3 — Backtesting

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

Reading note: pp. 32–36 (Excel, MATLAB, TradeStation and commercial platforms) were skimmed; they describe tools, not methods. Everything else (pp. 36–67) was read. In the extracted text the square-root sign is lost in prose (p. 44 prints "12 times"), but the code on pp. 45–46 shows `SQRT(252)`, which confirms the formula below.

## 1. Chapter summary (pp. 31–67)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Replicate every strategy yourself: it proves you understood it, exposes errors of the original research and lets you try variations. | Trusting unverified published results. | 31 |
| C2 | **Adjusted data** (splits, dividends): multiply earlier prices by a factor so returns stay unchanged; unadjusted data creates false signals at ex-dates. | Fake price jumps. | 36–40 |
| C3 | **Survivorship bias**: toy "buy lowest-priced stocks" gave −42% with delisted names included and +388% without them. Mitigation: record point-in-time data yourself from now on, or test on recent data. | Inflated results. | 40–42 |
| C4 | **High/low data is noisier** than open/close; a limit order "below the high" may not have filled. A sanity check: compute returns, inspect those beyond ~4 standard deviations, and require a news event or a market-wide move to explain them. | Backtests that profit from bad ticks. | 42–43 |
| C5 | **Sharpe and drawdown** are the two main measures (raw annual return needs too many qualifiers: denominator, leverage). Do **not** subtract the risk-free rate for dollar-neutral or intraday-only strategies (no financing cost); subtract it when the strategy incurs financing. **Annualised Sharpe = √N_T × Sharpe on period T**, where N_T is the number of periods in a year (N_T = 252 × 6.5 = 1,638 for hourly US-session returns; computing 252 × 24 is called a common mistake). Example 3.4: `SQRT(252)*AVERAGE(excess)/STDEV(excess)`. | Comparing strategies fairly. | 43–47 |
| C6 | **Drawdown computation** (Example 3.5): cumulative compounded return; running high watermark; drawdown = (1+HWM)/(1+cum) − 1; duration counter resets to 0 when drawdown is 0, else +1; maxima of both. Result for the example: 10.53% and 497 days. | Reproducible drawdown numbers. | 48–50 |
| C7 | **Look-ahead bias**: using information not yet available (e.g. the day's low, or regression coefficients fitted on the whole sample). Fix by lagging signal inputs. **Truncation test**: run on all data and save positions A; run on data truncated by the last N periods (10–100) and save B; cut A to the same length; they must be identical. | Silent future leakage. | 51–52, 59 |
| C8 | **Data-snooping bias**: rule of thumb ≤ **5 parameters**; qualitative choices (enter at open vs close, hold overnight…) also count; sample size ≈ **252 × number of free parameters** data points (stated as experience-based, not from literature), counted in *independent* observations (7 months of minute data for a daily model is only ~147 points). | Overfitting. | 52–53 |
| C9 | **Out-of-sample**: train first, test on the later part (roughly equal halves; at least test ≥ ⅓ of train). If test is poor, simplify the model. **Moving (rolling) optimisation** is the more rigorous version; "parameterless" model = parameters re-optimised in a moving lookback window; better to average over parameter sets than pick one best. **Paper trading** is the ultimate out-of-sample test, and the period since publication counts as out-of-sample if you did not tune on it. | Honest generalisation estimate. | 53–55 |
| C10 | **Sensitivity analysis**: vary parameters and make small qualitative changes; a model that works only at the exact optimum is overfit. Remove conditions one by one and keep removing while the **test** result does not degrade. Never add or tune to improve the test set (it becomes training). Then split capital across parameter values. | Fragile optima. | 60 |
| C11 | **Costs** (Example 3.7): a strategy with Sharpe 4.47 before costs on small caps had 0.25 on S&P 500 and −3.19 after 5 bp per trade. Treat results without survivorship-free data as upper bounds. | Costs and universe decide viability. | 60–65 |
| C12 | **Refinement**: small variations (e.g. act at the open instead of the close raised Sharpe from −3.19 to 0.78 after costs, Example 3.8); prefer refinements with an economic rationale, and any change must improve both train and test. | Improving without overfitting. | 65–66 |
| C13 | Summary honesty: skipping some precautions is acceptable for a first look; problems may still show only in paper/live trading. | Perfectionism vs progress. | 67 |

Chan's two worked pair-trading and mean-reversion examples are equity-specific (ETF pairs, S&P 500) and are not transferable as such; only the methodology is. No crypto advice appears in the chapter.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| C2 adjusted data | n/a | Crypto spot has no splits/dividends. Exchange-side events (symbol redenomination, delisting) are not handled. |
| C3 survivorship | ❌ | No delisting handling; universe chosen by hand. We could start recording point-in-time listings now. |
| C4 data sanity | ⚠️ | `Candle` has **no OHLC consistency check** (`high ≥ max(open, close)`, `low ≤ min(open, close)`, positive prices, non-negative volume) in `market_data/domain/models.py`. Only the risk module rejects *entries* on candles whose range exceeds `max_candle_range_pct`. The backtester has no such filter and no outlier report. |
| C4 coverage | ❌ | `find_gaps` exists and is shown in the coverage endpoint, but `BacktestService._check_candles` only requires **at least one** candle in the range, so a backtest silently runs over holes. |
| C5 Sharpe | ❌ | Not computed (see chapter 2). Annualisation convention undecided. |
| C6 drawdown | ⚠️ | Depth computed correctly (`max_drawdown_pct`); duration and watermark series missing. |
| C7 look-ahead | ✅ by construction, ❌ no regression test | Engine fills at next candle's open and the strategy sees only closed candles (`engine.py`). No automated truncation test (grep for `truncat`/`lookahead` in `api/tests` finds only a comment). |
| C8 snooping / sample size | ⚠️ | Strategies have ≤ 4 parameters. No sample-size check, no trial count in sweeps (`create_sweep` bounds the grid with `MAX_SWEEP_RUNS` but records no multiple-testing warning). |
| C9 out-of-sample | ⚠️ | One fixed split with the strategy running once over all data (`segments.py`). No walk-forward, no minimum-size rule. Paper trading exists and is mandatory before live. |
| C10 sensitivity | ⚠️ | Sweeps give the raw material, but no robustness view (e.g. neighbourhood stability of the best cell). |
| C11 costs | ⚠️ | Fixed fee and slippage (chapter 2). |
| C12 refinement | ✅ possible | Experiments are cheap; no governance around it. |

## 3. Opportunities

### O1 — Annualised Sharpe/Sortino with an explicit crypto convention *(book: C5 · convention is our adaptation)*
* **Book:** Sharpe = √N_T × mean/std of excess returns on period T; N_T must count real trading periods; a mismatch (252 × 24 for a session that has 6.5 hours) is an error.
* **Adaptation:** crypto trades 24/7, so N_T = 365 × (24 h / candle hours), e.g. 8,760 for 1h, 365 for 1d. Risk-free = 0 by default because the strategy is spot long-only with no financing, matching the book's rule (subtract only when financing exists); keep it configurable.
* **Problem:** metric absent. **Benefit:** the book's main comparison measure; ranks sweeps. **Complexity:** low. **Risk:** equity curves sitting flat in cash lower volatility and flatter the ratio; report **time in market** alongside; few returns give unreliable ratios (show sample size). **Validation:** reproduce the book's Example 3.4 numbers (Sharpe 0.7893 for IGE buy-and-hold) with the same inputs in a unit test; known-series tests.

### O2 — Drawdown duration and watermark series *(book: C6, pp. 48–50)*
Implement exactly the book's recurrence (duration counter resets at zero drawdown) and expose both series. **Complexity:** low. **Validation:** reproduce Example 3.5's definitions on a synthetic curve; ongoing drawdown reported as ongoing.

### O3 — Candle integrity validation *(book: C4, pp. 42–43)*
* **Proposal:** validate OHLC consistency and positive values at construction/import; reject or quarantine bad rows with a counter; add an outlier report (returns beyond k standard deviations; the book suggests ~4) that the operator can review; make the backtester optionally exclude/flag runs that cross flagged candles.
* **Note:** the book's "check against news or market-wide move" step is manual; here we could compare the move against other pairs (adaptation).
* **Benefit:** protects every backtest from bad data. **Complexity:** low–medium. **Risk:** over-eager filtering can delete real crashes; flag, do not silently drop. **Validation:** unit tests with malformed candles; integration test of the import job counters.

### O4 — Refuse (or loudly warn about) backtests over data gaps *(adaptation, motivated by C4/C11)*
Use the existing `find_gaps` inside `_check_candles`; return gap count/size in the run result and fail or warn above a threshold. **Complexity:** low. **Risk:** exchange maintenance windows are legitimate gaps; make it a warning with a tolerance. **Validation:** integration test with a hole.

### O5 — Look-ahead regression test (truncation test) *(book: C7, pp. 52, 59)*
Automate the book's procedure: run the engine on full candles and on candles with the last N removed, compare the **signals/positions** over the common prefix, for every registered strategy. **Complexity:** low (pure functions, fast). **Benefit:** guards the most dangerous silent bug whenever a strategy is added. **Validation:** the test itself, plus a deliberately leaky fake strategy that must fail it.

### O6 — Sample-size and parameter-count guard *(book: C8, pp. 52–53 · thresholds are the author's rules of thumb)*
Compute free-parameter count from the strategy's `PARAMETERS`, compare the number of **independent** observations (trades or bars, not ticks) with 252 × parameters, and emit a warning (not a block). Calibrate to crypto later. **Complexity:** low. **Risk:** the 252 rule is explicitly experience-based; treat as heuristic and make it configurable. **Validation:** unit test of the warning.

### O7 — Trial count and sensitivity view for sweeps *(book: C8, C10, pp. 52–60)*
Store the number of combinations on each sweep result; add a **neighbourhood robustness** view (does performance degrade smoothly around the best cell, or collapse?) and require the winner to also be acceptable in the test segment; never rank by the test segment. **Complexity:** medium. **Risk:** still no formal multiple-testing correction (later books address it). **Validation:** synthetic sweep with a single spike must be flagged fragile.

### O8 — Walk-forward (moving) optimisation *(book: C9, pp. 54–55)*
The book's rigorous out-of-sample method. Large feature: re-fit parameters in a lookback window and test on the next block, concatenating out-of-sample results. **Complexity:** high. **Risk:** compute cost; leakage if windows overlap wrongly. Keep as backlog **B-WALK-FORWARD** and plan after the chapters on cross-validation in Book 5.

### O9 — Cost sensitivity and break-even cost *(book: C11, pp. 60–65)*
Same as chapter 2 O4; re-run signals across fee/slippage grids and report where profitability disappears. **Complexity:** medium.

### O10 — Point-in-time listing log *(book: C3, p. 40 · adaptation)*
Start storing the exchange's symbol list and status daily so a survivorship-free universe exists later. **Complexity:** low; value grows with time, so cheap to start early.

### Not applicable
Split/dividend adjustment (C2), equity-universe examples (C11, C12 examples), platform choices (pp. 32–36).

## 4. Priority

| # | Item | Backtest quality | Reliability | Risk mgmt | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O5 truncation test | high | high | – | low | – |
| 2 | O3 candle integrity | high | high | medium | low–med | – |
| 3 | O4 gap guard | high | medium | – | low | `find_gaps` (exists) |
| 4 | O1 Sharpe/Sortino | high | – | medium | low | – |
| 5 | O2 DD duration | medium | – | high | low | – |
| 6 | O7 sweep trials/robustness | high | – | – | medium | O1 |
| 7 | O6 sample-size guard | medium | – | – | low | – |
| 8 | O9 cost sensitivity | high | – | medium | medium | O1 |
| 9 | O10 listing log | low now | – | – | low | – |
| 10 | O8 walk-forward | high | – | – | high | O1, O7, Book 5 |

## 5. Affected files
`market_data/domain/models.py` (Candle validation), `market_data/application/service.py` (import counters), `backtesting/application/service.py` (`_check_candles`, sweeps), `backtesting/domain/engine.py` (read-only for O5), `analytics/domain/metrics.py`, `backtesting/domain/segments.py`, new tests under `api/tests/unit` (truncation, metrics, candle validation), `docs/openapi.json`, app metric cards and sweep page.

## 6. Incremental plan
1. O5 truncation test for every registered strategy (no production code change).
2. O3 + O4 data integrity (domain validation, gap guard, import counters).
3. O1 + O2 metrics (pure functions, additive API fields, app display).
4. O7 + O6 sweep honesty (trial count, robustness, sample-size warning).
5. O9 cost sensitivity.
6. O10 listing log; O8 as a separate project later.

## 7. Acceptance criteria and tests
* Truncation test passes for all strategies and fails for a deliberately leaky one.
* Malformed candles are rejected or flagged with a count; no silent drops.
* A backtest over a gapped range reports the gaps.
* Sharpe/drawdown fixtures match hand calculations, including Example 3.4/3.5 style series; zero-variance returns give `None`.
* Additive API changes only; stored runs unaffected.
* Everything stays `Decimal` in the domain; ruff, mypy and all existing tests stay green.

## Caveats
Chan's numbers (≤ 5 parameters, 252 × parameters, 4 standard deviations, test ≥ ⅓ of train) are **his rules of thumb**, not statistical results, and were derived for equity strategies. Backtest results are not a guarantee of future returns; fees, slippage, overfitting and crypto-specific effects (24/7, fragmented liquidity, delistings) can all make live results worse.
