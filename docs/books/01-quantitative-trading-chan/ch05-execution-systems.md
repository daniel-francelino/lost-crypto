# Book 1 · Chapter 5 — Execution Systems

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

## 1. Chapter summary (pp. 79–94)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | An **automated trading system** retrieves data, runs the algorithm and submits orders. Fully automated minimises human error and delay and is indispensable for high-frequency; semi-automated (order file → basket trader) suits few waves a day. Often the order-generation program is the same as the backtest program. | Faithful execution of the backtested strategy. | 79–85 |
| C2 | Non-price inputs (dividends, estimates) must be fetched and parsed too. | Data beyond prices. | 80 |
| C3 | **Minimising transaction costs**: avoid low-priced stocks; **cap order size at about 1% of average daily volume** (a rule of thumb; example: 1% of IRN's volume = 510 shares ≈ $2,269); scale position size sub-linearly with market cap (fourth root keeps the largest-to-smallest ratio near 10) to keep diversification; splitting big orders trades market impact for slippage and is not suitable for small traders. Broker speed/risk checks cause slippage outside your control. | Market impact and illiquidity. | 87–88 |
| C4 | **Paper trading**: the only way to find software bugs without losing money; reveals look-ahead bias ("no way you could have had that data"); **compare paper trades and P&L with the backtest run on the same latest data; differences not explained by costs (including an expected execution delay) mean bugs**. Also gives intuition for P&L volatility, capital used, trades per day, operational timing. A month or more may reveal data-snooping, but attention to paper accounts fades, so snooping is usually revealed only by trading small real capital. | Verifying the implementation and the strategy out of sample. | 89–90 |
| C5 | **Why live diverges from backtest** — diagnose in order: (1) bugs, (2) do live trades match the backtest's trades, (3) execution costs higher than assumed, (4) illiquidity/market impact, then (5) **data-snooping** (test by removing rules and parameters: if the backtest collapses, snooping is likely; if still reasonable, bad luck is possible) and (6) **regime shifts** (examples: decimalisation in 2001; the plus-tick short-sale rule until 2007; hard-to-borrow shorts). You can never prove it was bad luck. | Disappointing live results. | 90–92, 93–94 |
| C6 | Summary of ATS benefits: adherence to the backtested strategy, running several strategies, speed. | – | 92–94 |

Chan's brokerage tools (DDE links, basket/spread traders, MATLAB, TradeStation) do not apply. Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| C1 same code for backtest and live | ✅ strong | The backtester and the paper trader share `execution/domain/fills.py` and `risk_management/domain/stops.py`; strategies are one class used by both. |
| C1 backtest uses live sizing | ❌ | The backtester sizes trivially (all cash in); live sizing/risk lives in `risk_management/domain/models.py::assess_signal` and is **not** applied in backtests. So backtest and live can diverge on position size, risk-per-trade sizing and entry rejections. (Documented in `engine.py` docstring, but it is a real divergence.) |
| C3 volume cap | ❌ | No limit tied to volume anywhere in `RiskLimits` or the trader (searched `volume` in `risk_management` and `trading`: no hits). Candle volume is stored but unused for risk. |
| C3 size-dependent impact | ❌ | Slippage is a fixed bps, independent of order size or liquidity. |
| C4 paper-vs-backtest comparison | ❌ | No tool compares a paper bot's fills/PnL with a backtest of the same strategy over the same period. `live_min_paper_days` gates promotion on **days elapsed** only (`bots/application/live.py:146`), not on agreement with the backtest. |
| C4 operational timing | ✅ | Worker heartbeat, stale-bot detection, reconciler every 60 s. |
| C5 divergence diagnosis | ❌ | No expected-vs-actual fill record (intended price at signal time, fill price, latency), so execution cost cannot be measured. |
| C5 snooping check by simplification | ⚠️ | Possible manually with sweeps; not packaged. |
| C5 regime shifts | ❌ | No regime tracking or alerts when live performance leaves the backtest range. |

## 3. Opportunities

### O1 — Backtest/paper parity report *(book: C4, p. 89)*
* **Problem:** nothing verifies that the system running the strategy does what the backtest says.
* **Proposal:** for a paper bot, re-run the backtester on the exact candles the bot saw over the same period (the same strategy parameters and costs) and diff signals and fills; show unexplained differences. Differences caused only by costs/latency are expected (the book's exception).
* **Benefit:** catches implementation bugs and look-ahead before real money. **Complexity:** medium. **Risk:** the live pipeline applies risk sizing the backtester does not; parity must either apply the same risk rules in the replay (see O2) or compare signals only. **Validation:** a replay of a known paper session must match; an injected discrepancy must be reported.

### O2 — Run the real risk module inside the backtester *(book: C1, pp. 79–85 · adaptation)*
* **Problem:** backtests assume all-in sizing, so reported risk and returns do not describe what a bot with `RiskLimits` would do.
* **Proposal:** an optional backtest mode that routes each signal through `assess_signal` with the bot's limits and applies daily-loss, drawdown and consecutive-loss pauses, so the replay reflects live behaviour.
* **Benefit:** backtest results that can be compared with paper/live. **Complexity:** medium–high (state such as day-start equity and consecutive losses is needed). **Risk:** two sizing modes produce two sets of numbers; label them clearly. **Validation:** with limits that never bind, results equal the current all-in mode; with binding limits, trades are reduced as expected.

### O3 — Liquidity cap relative to volume *(book: C3, p. 87 · threshold is the author's rule of thumb; applicability to crypto is an adaptation)*
* **Proposal:** a risk limit `max_order_pct_of_volume` using recent traded volume (e.g. a trailing average of candle volume in the base asset), applied in `assess_signal` and the backtester. Default off or conservative; for our account sizes it will rarely bind on major pairs, but it protects illiquid pairs.
* **Complexity:** low–medium (needs volume in the risk context). **Risk:** candle volume on one exchange is not total market liquidity. **Validation:** unit tests on the rejection and sizing.

### O4 — Record intended vs actual execution *(book: C3, C5, pp. 88, 90)*
* **Proposal:** persist the reference price at signal/decision time, the fill price and the latency per order; compute realised slippage per bot and compare it with the configured `slippage_bps`.
* **Benefit:** measures the cost assumption instead of guessing it; feeds chapter-2/3 cost sensitivity. **Complexity:** low–medium (new fields on orders, additive). **Risk:** testnet slippage is not representative of mainnet. **Validation:** integration test on paper fills.

### O5 — Divergence diagnosis checklist and dashboard *(book: C5, pp. 90–92)*
* **Proposal:** a per-bot view that follows the book's order — parity result (bugs), cost realised vs assumed, then a prompt to run the "remove parameters" simplification sweep (snooping), then a comparison of live return distribution with the backtest's (regime). Mostly composition of O1, O4 and sweeps. **Complexity:** medium. **Validation:** UI test on a bot with seeded data.

### O6 — Gate live promotion on parity *(book: C4, p. 90 · adaptation)*
* After O1 exists, add "paper result consistent with backtest" as an additional readiness check next to `live_min_paper_days`. **Complexity:** low once O1 exists. **Risk:** over-strict thresholds block promotion; make it a visible check with a clear explanation, still overridable only by the operator policy (not silently).

### Not applicable / deferred
Semi-automated tools, DDE, hiring consultants, market-cap weighting (single-asset bots), splitting orders over time (the book itself says it is unsuitable for small traders).

## 4. Priority

| # | Item | Reliability | Backtest quality | Risk mgmt | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O4 intended vs actual execution | medium | medium | medium | low–med | – |
| 2 | O1 parity report | **high** | high | medium | medium | – |
| 3 | O3 volume cap | – | – | medium | low–med | – |
| 4 | O2 risk inside backtest | – | **high** | high | med–high | – |
| 5 | O6 promotion gate | medium | – | high | low | O1 |
| 6 | O5 diagnosis dashboard | – | medium | – | medium | O1, O4 |

## 5. Affected files
`backtesting/domain/engine.py`, `backtesting/application/service.py`, `risk_management/domain/models.py`, `trading/application/trader.py`, `execution/domain/orders.py` and its ORM/repository (additive fields), `bots/application/live.py`, new tests in `api/tests/unit` and `api/tests/integration`, `docs/openapi.json`, app bot detail and readiness pages.

## 6. Incremental plan
1. O4: add intended price / latency to order records (additive).
2. O1: replay tool as a read-only service and endpoint, no effect on trading.
3. O3: volume cap as an optional limit.
4. O2: risk-aware backtest mode behind a flag.
5. O6, O5: gate and dashboard.

## 7. Acceptance criteria and tests
* Parity: a clean paper session shows zero unexplained differences; a seeded discrepancy is reported.
* Execution record: new fields nullable, old orders unaffected.
* Volume cap: off by default; with it on, oversized entries are reduced or rejected with a reason.
* Risk-aware backtest: identical to the current mode when no limit binds.
* No change to the live safeguards; ruff, mypy and all existing tests stay green.

## Caveat
The 1% of average daily volume rule is Chan's rule of thumb for equities and is not calibrated for crypto. Paper-trading fills simulate the market and cannot reproduce real liquidity or queue position.
