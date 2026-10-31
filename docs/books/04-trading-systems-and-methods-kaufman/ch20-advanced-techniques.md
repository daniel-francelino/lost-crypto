# Book 4 · Chapter 20 — Advanced Techniques

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 845–871 (volatility measurement and use, liquidity, trends and noise) were read in full. Expert systems, fuzzy logic, fractals/entropy, neural networks (pp. 890–894 read), genetic algorithms (pp. 901–902 read) and hedge-fund replication (start of p. 902) were only skimmed by headings and the pages named. The detail of fuzzy logic (876–879) and entropy (883–885) was **not** read.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Volatility is the second most important driver after price; use it for stops, targets, filters, sizing and portfolio construction. Volatility scales roughly with price level (lognormal); two assets at the same price can have very different volatility, which matters for equalising position risk. Longer measurement windows give higher volatility values, with a decreasing rate of growth. | Why measure volatility properly. | 845–850 |
| C2 | **Five practical measures**: (1) change over n days; (2) highest high − lowest low over n days; (3) **average true range (ATR)**; (4) sum of absolute daily changes; (5) **annualised standard deviation of returns** × √P. (1) depends only on two points and is always lower than the high/low based ones; (2) can size a stop if the holding period is known; (3) is the most popular and "gives a reasonable guideline for future volatility" (many strategies use `k × ATR` for stops, targets and risk); (4) misses gaps from the previous close. ATR is smoother than annualised volatility and shows smaller jumps when prices gap; both are converted to money by multiplying by price. Range-based measures use more data (highs and lows) and are more robust than close-to-close. Back-adjusted futures returns are distorted. Other estimators (Bookstaber close-to-close, high-low, high-low-close) are listed. | Choosing a volatility estimator. | 850–854 |
| C3 | **Relative volatility** `RV = V(n)/V(m)` with the longer window **lagged** so it ends before the shorter one starts (non-overlapping), which avoids the long window "absorbing" the recent spike and also helps after a volatile period. | A cleaner volatility ratio. | 855 |
| C4 | **Implied volatility / VIX**: generally inverse to the S&P; "buy when high, sell when low" folklore; implied vs historic volatility can diverge under stress (implied dropped faster after October 2008, spiked again in November while actual volatility fell). **VIX-based systems** (Connors reversal-9: 5 rules; Connors RSI(2) of VIX > 90 with the S&P above its 200-day MA; MarketSci EMA(10)/SMA(10) of VIX; Appel: buy at high VIX, no reliable sell signal): all rely on equity-index options data. | Using implied volatility. | 855–860 |
| C5 | **Intraday volatility and volume share the same U shape** (highest at open, lowest mid-session, up at close); correlation volatility–volume R = 0.595 in the NASDAQ 100 study; Brower's table of S&P rules predicting tomorrow's range (e.g. a high 3-day ATR is "a very good predictor of higher volatility"; RSI(3) < 40 predicts higher volatility; inside days predict lower; Monday lowest, Tuesday and Friday highest); On-Balance True Range. | Volatility is itself predictable (clustering). | 856–858 |
| C6 | **Volatility breakout** (Bookstaber): buy if the next close rises by more than `k × ATR` (k ≈ 3) from the current close; sell if it falls by more. | Breakout sized by volatility. | 860–861 |
| C7 | **Profit targets and stops from ATR**: `PT = entry ± k × ATR(t−1)` (k ≈ 3, triggered by intraday high/low); stops use the same `k × ATR`; stops triggered by high/low but exit at close to exploit noise. Targets are for **short-term** trading (more noise); in long-term trend following **taking profit or being stopped out loses the fat tail, so one must re-enter** while the trend is intact. | Adaptive stops and targets. | 861 |
| C8 | **Trade selection by volatility**: very high volatility at entry means very high risk and a worse return/risk ratio; extremely low volatility may mean no direction and small frequent losses; exiting when volatility spikes reduces both profit and risk but may come too late. Choose between **eliminating** a filtered trade and **delaying** it until volatility is acceptable (track the skipped trade; short-term trading eliminates, trend following delays). **Thresholds in standard deviations of a 20-day volatility** (1σ filters the top 16%, 2σ the top 2.5%, 3σ the top 0.13%; test values above 3 because the short window can exceed it). | Volatility as an entry filter. | 861–863 |
| C9 | **Entry filter results** (40-day MA trend, back-adjusted futures 1990–July 2011, cost $15 per trade): the low-volatility filter (threshold optimised in steps of 0.05 between 0.05 and 1.0) improved profit factor in all five markets, e.g. Eurodollars 2.11 → 2.5, crude 1.49 → 1.67, S&P 0.83 → 1.07 (a losing system "normally improves by removing trades"), Amazon 1.16 → 1.51; the high-volatility "only trade when above" filter also improved results, with inconsistent thresholds per market (S&P picked the maximum 3.0 to remove trades; crude 2.55). On Eurodollars the low-vol filter had an information ratio **1.143 vs 0.867** for the high filter and a smoother equity curve. | Evidence for the low-volatility entry. | 863–865 |
| C10 | **High-volatility exits** (40-day MA; exit when today's return exceeds the previous 20-day volatility × factor; do not re-enter until the trend changes), 30-year bonds 2000–2011: no exits profit factor 1.02 (net $4,500, 350 trades); exit at factor 10: 1.07 ($12,968); **exit and re-enter** when volatility returns to one quarter of the exit-day return: 1.16 ($34,781, 387 trades). Intent: in noisy markets take volatile profits; in trending markets a good move is followed by more. | Risk reduction by exiting shocks, with a reset rule. | 865–866 |
| C11 | **Trade selection summary**: filtering "always gets rid of good trades while, hopefully, removing more of the bad ones"; "you can't remove the risk, only delay it or move it around"; a system that seems to have no risk indicates a flaw in the development process. | Realism about filters. | 866 |
| C12 | **Liquidity**: many systems with good backtests fail when traded because the backtest assumes execution at relative highs/lows of the day where volume is minimal (Ginter and Ritchie, 1980). The profit of a countertrend system measured with a straight-line volume assumption concentrates at extremes where **no execution was possible**; for trend systems "no profits should be expected when orders are placed at the extremes". | Backtests that assume fills where there is no volume. | 867–868 |
| C13 | **Trends and noise**: noise (price shocks, many participants with different horizons) has statistics close to random: about half of moves change direction the next day, ~25% continue two days, 12.5% three days; the size of moves is also like a geometric distribution (50% small, 25% double, 12.5% four times). A single price move cannot be told from noise until it continues; as a trend's calculation period lengthens, fewer shocks trigger a change, so **longer trends are more reliable but suffer swings**; as markets mature **noise increases**, so the same returns need longer periods or yield smaller returns; mean reversion exploits the noise at short horizons ("noise dominates in the short term and trends in the long term"). Markets differ in noise (Eurodollars low; equity indices high; efficiency ratio, ch. 1). | Why trend speed trades off reliability. | 868–871 |
| C14 | **Interest rate carry** (rolling futures gives a carry): not relevant here. | | 871 |
| C15 | **Expert systems** (knowledge base + inference engine, if-then rules; forward chaining) — "no new published trading systems; any success is held confidential". **Neural networks**: inputs must be chosen and preprocessed ("critical"; more inputs mean slower solution and less robustness); success criteria must be explicit; they work better at predicting **forward-shifted technical indicators** than raw price direction (Ruggiero); data split about **70% training / 20% test / 10% out-of-sample validation**; training is trial and error "so the best results could be found by chance"; **fewer layers and neurons give more robust, more general solutions, while more allow specific patterns and overfitting**; start general and move toward specific. **Genetic algorithms**: chromosomes of rule genes, fitness, propagation, mating, mutation (about 10% mutated; fewer than 5% changed converges to the initial pool, more than 25% loses the best); convergence when average fitness stops improving; use 70–80% of data for search, the rest out-of-sample ("normally deteriorates but must still meet minimum criteria"); **multiple seeding** (run several random starts to avoid a local peak). **Hedge-fund replication**: regression of fund returns on market factors with Solver. | Machine-learning style methods in 2013 form. | 871–902 |

Examples are futures/stocks; crypto remarks below are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| ATR / realised volatility | ❌ | Not computed in `strategies`, `analytics` or `risk_management`. |
| Stops from volatility | ❌ | Fixed percentage `stop_loss_pct` only (`risk_management/domain/stops.py`). |
| Volatility entry filter | ❌ | `max_candle_range_pct` rejects a signal if the signal candle is too wide (a one-bar volatility cap) — the only volatility-related guard (`assess_signal`). It is a fixed percentage and has no relation to recent volatility. |
| Position sizing from volatility | ❌ | Risk-per-trade is derived from the stop distance, which is a fixed percentage (ch. 23 will cover this). |
| Relative volatility / shock ratio | ❌ | None. |
| Liquidity check (volume cap on order size) | ❌ | `Candle.volume` unused; fills are at next open with fixed slippage. |
| Fill realism at extremes | ✅ (partial) | Entries fill at the **next open**, not at the extreme of the signal candle; stops fill at the stop price or the open on a gap (rule for gap-through-open). This avoids the "fills at the extreme" error in C12. |
| Machine-learning / genetic search | ❌ | `sweeps` are grid searches (`MAX_SWEEP_RUNS`) with no correction. |
| Out-of-sample split | ✅ (partial) | One chronological train/test split (`segments.py`); no third lock segment (book 3 ch. 6 O5). |

## 3. Opportunities

### O1 — Shared volatility toolkit: true range, ATR, close-to-close σ, and ranged versions *(book: C2, pp. 850–854)*
Implement true range, ATR (Wilder or simple, documented), rolling standard deviation of log returns (with the 365-day annualisation of book 1 ch. 3 O1) and the high-low range measure, in one helper module used by diagnostics, strategies, risk and sizing. Book guidance: prefer range-based measures (they use highs and lows); ATR for stops; annualised σ for risk reporting and comparisons. **Complexity:** low (shared with ch. 18 O1). **Validation:** hand-computed fixtures, scale invariance, gap handling (true range includes the previous close).

### O2 — ATR-based stop distance (and optional target) as an alternative to a fixed percentage *(book: C7, p. 861)*
* **Proposal:** a stop mode `atr` with `stop = entry − k × ATR(n)` computed at entry from closed candles (book: k ≈ 3). Keep the percentage mode as default. Optionally `target = entry + k_t × ATR` for short-horizon strategies only, as the book restricts targets to short-term trading.
* **Why:** a fixed 2% stop is far too tight in volatile phases and too wide in quiet ones; an ATR stop adapts the risk distance, and the position-size formula (risk per trade ÷ stop distance) then yields volatility-scaled sizes automatically.
* **Caveats from the book:** for long-term trend following, stops and targets cost the fat tail; **re-entry** logic is needed or the trend profit is lost (see ch. 8 O7 ablation). Native exchange stops mean the stop level must be fixed at entry (a trailing ATR stop needs order replacement; see ch. 19 O2).
* **Complexity:** medium (`StopMode` in risk config, backtester and trader, form fields, tests). **Risks:** more parameters; ATR from the entry candle may be inflated by a breakout bar. **Validation:** ablation (percent vs ATR) via the pipeline; parity backtest/paper; the computed stop is deterministic and logged.

### O3 — Volatility entry filter, with "delay" and "eliminate" modes *(book: C8, C9, pp. 861–865)*
* **Proposal:** a risk-config filter that suppresses (or delays) an entry when the **20-bar volatility** sits above/below thresholds expressed in standard deviations of its own history (the book's way of making thresholds probabilistic). Two policies: **eliminate** (skip the signal) and **delay** (keep the entry pending until volatility re-enters the acceptable band, still requiring the trend condition to hold).
* **Evidence in the book:** the low-volatility entry filter improved every one of five tested markets, and the information ratio and smoothness improved on Eurodollars. **But** (a) the thresholds were optimised per market (0.05–1.0 in steps of 0.05), so the improvement is in-sample; (b) the book itself reports inconsistent thresholds for the high filter; (c) the S&P result shows that filtering a losing system "improves" it without making it good; (d) markets were futures, back-adjusted, 1990–2011, cost $15.
* **Crypto note (ours):** the relationship is not guaranteed; crypto trends often start from **low-volatility compressions** (breakouts), so "enter only when volatility is low" could cancel good breakouts while "enter only when volatility is high" could chase. Treat as **H-VOL-FILTER**, tested with both directions and with cost sensitivity through the evidence pipeline (book 3 ch. 6 best-of-N and lock).
* **Complexity:** medium (pending-entry state in the engine and trader). **Validation:** truncation test; delayed entries only use data up to the entry candle; counts of eliminated/delayed signals.

### O4 — Shock exit with re-entry reset (experiment) *(book: C10, pp. 865–866)*
Exit when the bar's return exceeds `f ×` the previous 20-bar volatility; re-enter in the same trend only after the bar-to-bar volatility falls to a quarter of the exit bar's move. The book's improvement (profit factor 1.02 → 1.16) was on one market (30-year bonds, 2000–2011) with a factor 10 chosen by the author, so evidence is thin. For spot long-only crypto only the **downside shock** is relevant (an extreme red candle while holding). Combine with ch. 14 O1 detection and the gap-risk limits. **Complexity:** medium. **H-SHOCK-EXIT.** **Risks:** exit after the damage is done (the book says so); re-entry logic complexity; stops already protect gap risk on the exchange.

### O5 — Fill realism: volume-aware execution cap and extreme-fill guard *(book: C12, pp. 867–868)*
* **Proposal:** (a) an optional **volume cap**: reject or reduce simulated fills whose quantity exceeds a fraction (for example 1–5%) of the candle's traded volume (and report the count); (b) a regression test/audit that backtest fills never occur at the signal candle's high or low (current engine fills at the next open, so this protects against regressions when limit orders or intrabar fills are added).
* **Benefit:** small accounts rarely hit this, but the user can scale `capital`; the Ginter–Ritchie warning applies if limit orders and intrabar fills are added later (ch. 5 O2, book 2 ch. 7). **Complexity:** low. **Validation:** a fill larger than the cap is reduced/rejected deterministically; default behaviour unchanged.

### O6 — Volatility clustering as a documented expectation and a test *(book: C5, pp. 856–858)*
Brower's rules (high 3-day ATR predicts higher volatility; inside days predict lower volatility) restate **volatility clustering**: volatility is much more predictable than direction. Add a diagnostic ("autocorrelation of absolute returns" and "does last-3-bar ATR predict next-bar range") to the series diagnostics, as the validation that ATR-based stops/filters are using a forecastable quantity. **Complexity:** low. The weekday figures (Monday lowest, Tuesday/Friday highest) belong to the S&P in 1987–95 and should not be assumed for crypto, which trades 7 days a week.

### O7 — Noise-aware design rule for trend speed *(book: C13, pp. 868–871)*
Document, and show in the UI, the book's trade-off: faster trend rules trigger on more noise (more trades, more fee drag), slower rules are more reliable but lag; as noise rises the same strategy yields lower returns (our adaptation: crypto noise also changes over regimes, so a parameter that worked in a high-trend regime may deteriorate). Concrete deliverable: efficiency-ratio (book 4 ch. 1 O1) next to each sweep result, so users see **noise vs period** before picking a parameter. **Complexity:** low.

### O8 — ML/genetic search discipline (guidance only, no implementation) *(book: C15, pp. 890–902)*
If optimisation tooling grows beyond the grid sweep: (1) keep search separate from out-of-sample; (2) the book's own splits (70/20/10 for neural nets; 70–80% search, rest out-of-sample for genetic algorithms) are a **minimum**, and the final 10% lock must be used once; (3) **multiple seeding**: repeat the search from several random starts and compare solutions to detect local peaks; (4) prefer fewer parameters ("fewer layers and neurons produce more robust, general solutions"); (5) treat a search result as a hypothesis, since "the best result could be found by chance". These map to the pipeline already proposed (best-of-N, permutation, locked validation) and to book 5's cross-validation methods; there is nothing to build now. **Complexity:** none.

### Not applicable
VIX systems (no equivalent implied-volatility index with a tradable instrument in this scope; an equivalent for BTC exists as options-derived indices but is outside the data we hold), interest-rate carry, fuzzy logic (not read), expert systems, entropy (not read), hedge-fund replication, Excel Solver procedures, intraday options gamma/theta trading.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 volatility toolkit | medium | high | – | low | – |
| 2 | O7 noise next to sweep results | medium | – | – | low | ER helper (ch. 1/17) |
| 3 | O6 volatility-clustering diagnostic | low | medium | – | low | O1 |
| 4 | O2 ATR stop mode | – | high | medium | medium | O1; live stop design |
| 5 | O5 volume cap and extreme-fill guard | medium | medium | – | low | – |
| 6 | O3 volatility entry filter | medium | medium | – | medium | O1; pipeline |
| 7 | O4 shock exit and re-entry | low | medium | – | medium | O1; ch. 14 O1 |
| 8 | O8 search discipline | – | – | – | none | book 5 |

## 5. Affected files
`strategies/domain/` or a new shared `indicators` helper (verify naming against the existing layout; no empty `__init__.py`), `risk_management/domain/` (stop mode, filter config, sizing from stop), `backtesting/domain/engine.py` (pending entries, fill cap), `trading/application/trader.py` and `execution` (stop at entry), `analytics` (diagnostics), `docs/openapi.json`, app forms and chart display, tests.

## 6. Incremental plan
1. O1 toolkit and diagnostics (O6, O7) — read-only, no behaviour change.
2. O5 guard (default off).
3. O2 ATR stop in backtest and paper, with percent-vs-ATR ablation; live only after parity.
4. O3/O4 experiments through the pipeline with explicit eliminate/delay variants.

## 7. Acceptance criteria and tests
* ATR, true range and σ match hand-computed fixtures including gaps; scale-invariant; reproducible.
* Stop mode `atr` is deterministic and logged; percent mode unchanged; the sizing result changes consistently with stop distance.
* Volatility filter never uses data after the decision candle (truncation test); counts of eliminated/delayed entries reported.
* Fill cap: oversize fills reduced/rejected with a counted reason; default off reproduces current results bit-for-bit.
* ruff, mypy and all existing tests green.

## Caveats
All performance tables (Tables 20.2, 20.3) come from back-adjusted futures and one stock, are optimised in-sample, and use fixed small costs; the high-volatility-exit result rests on one market. The author does not apply multiple-testing corrections. The volatility spike and "buy when VIX is high" lore concern equity indices and implied volatility. The sections on fuzzy logic, entropy and the full chapters on neural networks/genetic algorithms were not read in full, so no claim is made about them beyond the cited pages.
