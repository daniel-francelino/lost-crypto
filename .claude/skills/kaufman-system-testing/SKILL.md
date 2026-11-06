---
name: kaufman-system-testing
description: System-testing discipline from Perry Kaufman's "Trading Systems and Methods" (5th ed.) ch. 21-22 and ch. 2 — set expectations before testing, fix parameter ranges beforehand, geometric parameter grids, in/out-of-sample and step-forward tests, parameter maps and plateaus, neighbor averaging, sensitivity and cost tests, robustness criteria (few variables, many markets), ten performance criteria, "is the model broken?" monitoring, data cleaning and paper trading. Use when designing a parameter sweep, reading a sweep heat map, choosing among parameter sets, or deciding if a strategy is robust enough to go live.
---

# System testing (Kaufman, *Trading Systems and Methods*, ch. 21, 22, 2)

Page numbers are book pages (the PDF is the book + 20). **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (it studies futures and stocks; its slippage and cost figures are futures-specific). Chapter analyses: `docs/books/04-trading-systems-and-methods-kaufman/ch21-system-testing.md` (the book's most relevant chapter for our sweep), `ch22-*.md`, `ch02-*.md`. Parts of ch. 21-22 were read only partly in those analyses (e.g. the final robustness list, pp. 977-982). Pairs with `aronson-data-mining-bias`, `chan-backtest-hygiene`, `walk-forward-validation`.

## 1. Mindset (pp. 905-908)
- Testing is a contest between computing power and common sense; **optimization is the most misused technique** — best test results never match expectations and can end as a financial tragedy.
- **Expectations first**: define the idea, horizon, relative risk and expected hit rate **before** testing, or you cannot tell a good idea from overfitting. "Testing should help decide between risk/reward profiles, **not discover strategies**."
- Define the objective: profit alone yields one or two big winners and many small losses; the industry prefers Sharpe/information ratio; also consider max drawdown and profit per trade (costs).

## 2. Parameters and ranges (pp. 908-910)
- Fix each parameter's range **before** testing (RSI 3-10, not 3-50; if a 45-day RSI wins, the concept is probably overfit) (p. 940). 250 x 30 x 30 = 225,000 tests; limiting the test forces an early decision on reasonable ranges.
- **Do not space periods evenly**: 49 vs 50 days differs 2%, 2 vs 3 days 50%. Use all small values and fewer large ones, or **multiply by ~1.5 each step** (p. 909). For smoothing constants, equal spacing of constants is better than equal spacing of days (p. 299-301).
- **Order**: test the most important component first (trend period), then timing, then stop-loss; "it is unrealistic to think the stop size should command a strategy". Distinguish continuous, discrete and **coded** (rule/regime) variables (pp. 909-910).

## 3. In/out of sample and step-forward (pp. 27-28, 916-919)
- Reserve **~50%** out of sample (first/last half, alternating blocks, or fixed random alternating blocks of 2-8 years); evaluate **daily returns**, not total profit, in alternating blocks. "In-sample data can be tortured mercilessly; out-of-sample is used **once**." Out-of-sample usually earns ~50% of in-sample; an information ratio drop 2.0 -> 1.0 is "reasonably good". Adjusting after seeing out-of-sample is **feedback — always overfitting**.
- **Step-forward**: choose parameters on a window (e.g. 2 years), apply to the next 6 months, step 6 months, accumulate **only** out-of-sample results. Short windows favour fast systems; if the optimum jumps between short and long across windows (10, 50, 15...), use longer windows (5 years). Repeated runs consume the out-of-sample, so keep a final untouched set.
- Sampling error ~ **1/sqrt(N)**: 1 trade 100%, 4 trades 50%, **400 trades 5%**; slow systems with 2-3 trades a year must be applied to many markets to reach a useful N (pp. 28-29). Data must include rising, falling and sideways periods; ten bullish years make any long strategy look good (p. 29).

## 4. Searching without fooling yourself (pp. 919-936)
- The best set is the most **robust**, not the maximum. Sequential optimization (one parameter at a time) cuts n1xn2xn3 tests to n1+n2+n3 but can miss the peak (finds 300 instead of 400); mitigate with **random restarts** (same answer from several seeds suggests the peak was found).
- **Parameter maps**: broad profitable plateau (good); two plateaus (fast vs slow — prefer slow for costs/errors); a **narrow spike surrounded by losses** (likely a passing shock; high profit without costs is also suspect). **Erratic patterns mean an unreliable system or a test error.** If averages are equal, the lower standard deviation of profit factor means more stability (pp. 922-929).
- **Neighbor average**: average each cell with its 9 neighbors (6 on edges, 4 in corners) to smooth peaks (pp. 930-932).
- Large searches: 8 parameters can reach **2,332,800,000** combinations. Genetic-algorithm recipe: populations of 1,000-5,000 strings, crossover 10-15%, mutation in 10% of strings, stop on convergence, **repeat up to 5 times with different seeds, keep the top 20 strings** — clustering suggests robustness, divergence casts doubt. **Monte Carlo sampling** of parameters (1,000 random strings, check each value is sampled about equally, repeat) also shows the **depth** of success (pp. 932-936).
- **Refining rules**: a rule that fixes one specific loss raises the peak but worsens neighbors; **very high kurtosis** of the performance-vs-parameter distribution signals overfitting; a good change improves **all** cases (pp. 937-938).

## 5. Robustness criteria (pp. 939-945)
1. A **sound premise**: each rule exploits a real phenomenon. 2. **Adaptation**: volatility-scaled stops, risk-based size, no fixed levels or dollars. 3. **Appropriate testing** on most of the data. Futures Truth found the best systems have **four or fewer variables**. "A robust system performs consistently with the minimum of parameters tested on more data."
- Evaluate by the **average of all tests**, not the best; `adjusted return = mean of all tests - 1 standard deviation` (84% chance of achieving it under normality). Review outliers: the result must not depend on one big move, especially a shock; "several big profits and no big loss indicate overfitting".
- **Sensitivity test**: shift parameters individually and jointly by small amounts; performance should be moderately sensitive. If all neighbors are worse, it is a **peak solution (overfit)**. Group tests by distance from the center in concentric shells and watch the mean fall by shell (pp. 943-944).
- "Significance of the significant" depends on the total number of attempts across **all** strategies, not only the current one. 70% profitable tests is a rule of thumb only before narrowing the range. **Cross-market check**: profitable on S&P but not NASDAQ => probably overfit; related markets act as out-of-sample; "loose trousers fit everyone" (Tropin) — expect suboptimal but consistent results (pp. 944-945, 954).
- **Costs**: the profitable range of a moving average on NASDAQ narrowed from periods above 15 days to ~45-75 as the round-trip cost rose from zero to US$150 (p. 949).
- **Use the losing region**: a persistently losing zone can be a fast countertrend inside a slow profitable trend (profit factor 1.51 -> 2.26, trades 212 -> 72; one market) (pp. 950-951).
- **Retest** with all data at the end; parameters should change little; retest after **5-10% new data**; after a shock do not create rules to fix it (pp. 951-952).

## 6. Ten performance criteria to report (pp. 941-942)
Profit factor / return ratio; net profit; **number of trades** (few are unreliable); **% profitable** (30-40% is normal for trend; > 60% often means small recurring profits); **average net return per trade vs costs**; **max drawdown** (erratic, not the future maximum; a surprisingly small drawdown means overfitting or a short test; prefer the **average of max drawdowns across tests**; typical capital is 3x that); annualized return; **time to recover**; **time in market**; **slope of periodic returns** (a falling slope signals deterioration).
Statistics notes (ch. 2): daily-return **kurtosis above 7-8 may indicate overfitting** (too many similar profitable trades) (p. 40); monthly data look less volatile than daily (S&P 1990-2010: 18.6% daily vs 15.3% monthly) so use daily (p. 53); annualize standard deviation by the **square root** of the number of periods; use a two-sample t-test on net trade returns of two non-overlapping periods for consistency (pp. 43-48).

## 7. Is the model broken? (pp. 951-953)
Compare live drawdown size/duration with the tested profile; persistent losses up to the old maximum drawdown flag a problem. Probability of a drawdown >= P under normal returns: `Prob = (1 - P)^(2 mu / sigma^2)` (annual return 30%, mu/sigma = 0.09 daily: exponent 23.51; at 95% confidence a 12% drawdown is expected in ~5% of months). Normality makes this optimistic.

## 8. Practical (ch. 22, pp. 983-990)
- **Too much computing power** (indicator cauldron + brute force/neural/genetic) is overfitting; less power forces thinking ahead.
- **Data checks (daily)**: outliers > 4% from the previous value or a preset %, missing dates (> 4 days flagged), open/close outside the high-low range (impossible). **Intraday**: frequency vs average per 5-minute interval, large jumps that reverse in seconds. A system built on clean data can generate many extra live signals from bad prices (p. 986).
- **Paper trading** is the safest final check because the out-of-sample set always ends up used more than once; document expectations first (trade frequency, holding time, hit rate, size of wins/losses); in paper, assume the **worst price in the 5 minutes after an intraday signal**; start small (p. 988).
- **Build vertically**: the core rule must be profitable alone, each feature tested on top; compare the % of profitable parameter combinations with and without a feature; transparent systems beat complex ones (pp. 988-990).
- **Debug list** (pp. 990-991): ambiguous rule, technique not working in range, works in some markets only, assumptions on selected data, ignoring large losses (LTCM), misjudged volatility, market evolution.

## 9. [Adaptation] Sweep checklist for the bots
- [ ] Expectations (hit rate, trades/yr, hold time, risk/reward) written before the sweep.
- [ ] Ranges fixed in advance, grid geometric (~1.5 steps), total trials logged.
- [ ] Heat map inspected: plateau, not spike; neighbor-averaged score used to rank.
- [ ] Rank by average over a reasonable range and `mean - 1 sd`, not the maximum.
- [ ] Out-of-sample used once; step-forward with long enough windows; final untouched window.
- [ ] Cost ladder with real fees + funding; slippage assumed from our own fills, not the book's futures numbers.
- [ ] Same rules checked on several symbols; <= 4-5 free variables.
- [ ] Number of trades >= useful N; kurtosis and outliers reviewed.
- [ ] Live monitoring uses expected drawdown profile and the `Prob` formula as a tripwire.
No result guarantees future returns.
