# Book 1 · Chapter 7 — Special Topics in Quantitative Trading

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

Reading note: all of pp. 115–156 was read. MATLAB listings (Examples 7.4, 7.6, 7.7) and the vendor-tool Example 7.1 were read for their claims, not reproduced.

## 1. Chapter summary (pp. 115–156)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Strategies profit only if prices are **mean-reverting or trending**; otherwise they random-walk. Both can hold on different horizons. The author finds general theories of either not very useful and says it is usually safe to assume mean reversion unless expected earnings changed (his view, with Khandani–Lo cited as a simple profitable-before-costs reversal model). | Choosing the type of edge. | 116–117 |
| C2 | Mean-reversion backtests are **inflated by bad quotes** (a fictitious low quote is bought, the next correct quote sells at a profit) and by survivorship bias. Data must be cleansed before trusting them. | Fake profits. | 117 |
| C3 | Momentum sources: slow information diffusion (e.g. post-earnings drift), incremental execution of a large order, herd behaviour. The last two have **unpredictable time horizons**. | When trends exist and how long. | 117–119 |
| C4 | Competition effects: mean-reversion edge shrinks toward zero and later signals more often reflect real valuation changes; momentum's **time horizon shortens** (a one-week hold may become one day, then unprofitable). | Edge decay. | 119, 140 |
| C5 | **Regime switching**: bull/bear, volatility, mean-reverting/trending. Volatility regimes suit classical econometrics (GARCH) but help options traders, not stock traders. Hidden-Markov models assume **constant transition probabilities** and are said to be generally useless for trading; "turning-point" models are a data-mining approach. Example 7.1 (a perceptron on a brokerage stock): 37.93% gross over **six months**, 89 trades, vs 15.77% buy-and-hold; the author himself notes the short period and that the optimisation window was not fully out-of-sample. | Detecting when rules change. | 119–126 |
| C6 | **Stationarity/cointegration**: a stationary series is a mean-reversion candidate; two non-stationary prices can combine into a stationary spread (hedge ratio by regression; test with cointegrating ADF). **Cointegration ≠ correlation**; KO/PEP are correlated (0.4849) but not cointegrated. Stationarity guarantees profit only while it persists; non-stationary series can still have short-term reversal. Examples need **shorting**. | Pair trading logic. | 126–133 |
| C7 | **Factor models** `R = Xb + u` (exposures, factor returns, specific returns); Fama–French three factors; PCA as a returns-only factor model; works only if factor returns have momentum; the author's PCA strategy on small caps lost money; fundamental-factor models suffer long drawdowns when investor preferences change. | Explaining/forecasting cross-sectional returns. | 133–139 |
| C8 | **Exit strategies**: fixed holding period, target price, latest entry signal, stop price. For mean reversion, estimate the holding period robustly from the **Ornstein–Uhlenbeck** model: regress `dz` on `z`, **half-life = ln(2)/θ** (GLD/GDX ≈ 10 days); exit at the mean or after the half-life. For momentum, the holding period from a small number of trades is error-prone. **Exit on a fresh opposite entry signal acts like a stop without an extra parameter**; a reversal model should not use a stop-loss (exit at the worst moment) unless it enters a momentum regime. | How to leave trades. | 140–143 |
| C9 | **Seasonality**: equity calendar effects have weakened (his tests of the January effect and a year-on-year effect, Examples 7.6–7.7); commodity-futures seasonality persisted because it rests on real demand, but occurs once a year so snooping is hard to rule out: vary dates and require an economic rationale. | Calendar strategies. | 143–151 |
| C10 | **High-frequency**: more bets per day → higher Sharpe (law of large numbers) → more leverage; risk is easier to manage (deleverage fast); needs bid/ask/book data, careful cost modelling, and fast execution; often only real-time testing is conclusive. | Why short-horizon strategies score high. | 151–153 |
| C11 | **High leverage vs high beta**: growth depends on Sharpe², so prefer a low-beta portfolio levered up (caveat: Gaussian assumption, fat tails). | How to raise returns. | 153–154 |

Most examples are equity pairs, ETFs, commodity futures and shorting. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Strategy catalogue vs C1 | ⚠️ trend only | Both strategies are trend/breakout, long-only (`ema_crossover`, `donchian_breakout`). There is no mean-reversion strategy; none uses volatility regimes. |
| C2 bad quotes | ⚠️ | Only entry-time filter `max_candle_range_pct` in the risk module; no data cleansing (see chapter 3 O3). Relevant for any future mean-reversion strategy. |
| C5 regime detection | ❌ | No regime measure of any kind. |
| C6 pairs/cointegration | ❌ and **not feasible as is** | Needs shorting or a hedge leg; the system is spot long-only, one asset per bot. |
| C7 factor models | ❌ | Single-asset bots; no cross-sectional universe. |
| C8 exit by opposite signal | ✅ | Both strategies exit on the opposite signal (EMA cross back; close below the lowest low of `exit_period`); the book calls this the principled stop for momentum models. |
| C8 optional stop/target | ✅ | `stop_loss_pct`/`take_profit_pct` parameters on both strategies, plus the risk-module sizing from the stop. |
| C8 fixed holding period / time stop | ❌ | No time-based exit (searched `max_hold|holding` in `strategies/domain`: nothing). |
| C8 half-life estimate | ❌ | Not applicable until a mean-reversion strategy exists. |
| C9 seasonality | ❌ | None; calendar features not available to strategies. |
| C10 high frequency | ❌ | Smallest timeframe is 1 minute candles; no order book/bid-ask data; the fill model uses the candle open. Not suited to HFT. |
| C11 leverage vs beta | n/a | No leverage. |

## 3. Opportunities

### O1 — Add a mean-reversion strategy family *(book: C1, C8, pp. 116–117, 140–143 · crypto applicability is an adaptation)*
* **Problem:** the catalogue only covers trending markets; the book says mean reversion is the more prevalent regime in stocks. Whether that holds in crypto is **not established by the book**; it must be tested on our data.
* **Proposal:** a long-only mean-reversion strategy (for example a z-score of price against a moving average, entering when far below and exiting at the mean or after a holding limit), implemented exactly like the others (one class, registered in the catalogue, parameters validated).
* **Benefit:** diversifies edge type; enables meaningful use of the book's exit rules. **Complexity:** medium.
* **Risks:** high exposure to the data errors of C2 and to "catching falling knives" in crypto crashes; a stop-loss is wrong for this family (C8) but a hard risk cap is still needed. Long-only spot loses half the book's logic (the short side).
* **Validation:** backtest with and without costs; truncation test (chapter 3 O5); test segment results; sensitivity of the entry threshold.

### O2 — Time-based exit (holding-period limit) *(book: C8, p. 140)*
* **Proposal:** optional `max_holding_candles` on strategies/bots that exits after N candles; for momentum-type strategies pick N from backtests knowing the book's warnings about error and decay; for mean-reversion use the half-life (O3). **Complexity:** low. **Risk:** another parameter (snooping budget, chapter 3 O6). **Validation:** engine test that a position is closed on the right candle.

### O3 — Half-life of mean reversion as an analysis tool *(book: C8, pp. 140–142)*
* **Proposal:** a research endpoint/function that fits `dz = θ(z − μ)dt + noise` by regression on a price or spread series and returns `half-life = ln(2)/θ`, to inform holding periods and lookback choices. Only meaningful if θ is negative and significant; return `None` otherwise. **Complexity:** low–medium (OLS in `Decimal` or a documented float boundary, see money rules). **Risk:** crypto prices are rarely stationary; a spurious half-life from a trending series is misleading. **Validation:** synthetic Ornstein–Uhlenbeck series with known θ; random walk must yield no result.

### O4 — Volatility-regime indicator (simple, descriptive) *(book: C5, pp. 119–120 · adaptation)*
* **Proposal:** report realised-volatility percentile and trend/range flags per backtest segment so results can be read by regime; do **not** trade on regime predictions yet (the book itself is sceptical of HMMs and its own example is a six-month test). **Complexity:** low. **Validation:** synthetic series with a volatility step.

### O5 — Data cleansing before mean-reversion work *(book: C2, p. 117)*
Dependency of O1: implement chapter 3 O3 (candle integrity and outlier report) first.

### O6 — Seasonality / calendar features *(book: C9, pp. 143–151 · low priority)*
Crypto has day-of-week and funding-time patterns that the book does not discuss; the book's only lesson is the discipline: economic rationale, vary the dates, and expect decay. Defer until the core metrics exist.

### Not recommended now
* **Pairs/cointegration, factor models, PCA** (C6, C7): need shorting and a multi-asset universe; revisit only if futures/margin or a multi-asset portfolio engine is introduced.
* **HMM or perceptron regime prediction** (C5): the book's own evidence is a six-month, gross-of-costs example by a vendor tool.
* **High-frequency** (C10): requires order-book data and low-latency execution.
* **Leverage vs beta** (C11): no leverage.

## 4. Priority

| # | Item | Backtest quality | Reliability | Risk mgmt | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O5 data cleansing | high | high | – | low–med | chapter 3 O3 |
| 2 | O2 time-based exit | low | – | medium | low | – |
| 3 | O3 half-life tool | medium | – | – | low–med | – |
| 4 | O4 regime descriptors | medium | – | – | low | chapter 2 metrics |
| 5 | O1 mean-reversion strategy | medium | – | medium | medium | O5, chapter 3 O5/O7 |
| 6 | O6 seasonality | low | – | – | low | – |

## 5. Affected files
`strategies/domain/` (new strategy file, registry entry, optional exit parameter in `base.py`), `strategies/catalog.py`, `backtesting/domain/engine.py` (time exit), `analytics/domain/` (half-life, volatility regime), app strategy forms (`lib/shared/strategies/params.ts`), `check:consistency`, tests.

## 6. Incremental plan
1. Data integrity first (chapter 3 O3).
2. Time-based exit parameter + tests.
3. Analysis tools: half-life and regime descriptors.
4. Mean-reversion strategy, gated by the truncation test, trial counting and cost sensitivity from earlier chapters.

## 7. Acceptance criteria and tests
* Any new strategy passes the truncation test and has parameter validation like existing strategies.
* Half-life returns the known value on a synthetic series and `None` on a random walk.
* The time exit closes at the specified candle and is covered by engine tests.
* No change to existing strategies' behaviour; ruff, mypy, all tests green.

## Caveats
Every performance figure in this chapter is a 2008-era equity or futures example, mostly gross of costs and several with survivorship bias that the author states himself. The claim that mean reversion is more prevalent than momentum is the author's view for stocks and **must not be assumed for crypto**. Nothing here is evidence of future profitability.
