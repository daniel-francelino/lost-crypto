# Consolidated backlog — proposals from the five books

Status: **proposals only; nothing is approved or implemented.** Each item lists the chapter reports where it appears (book number · chapter). Effort: S (days), M (about a week), L (weeks). "Confidence" is how strongly the books support the item *and* how well it fits a spot, long-only, one-asset-per-bot platform. Crypto adaptations are ours; the books do not cover crypto.

Baseline of the code: [00-system-baseline](00-system-baseline.md).

## A. Evidence and validation (highest value: counters overfitting, which all five books name as the main risk)

| ID | Item | Where it comes from | Effort | Confidence |
|---|---|---|---|---|
| A1 | **Trial ledger**: record every backtest and sweep member per dataset and strategy family; show raw and effective counts | 1·2, 3·6, 4·21 (O2), 5·1 (O3), 5·8 (O1), 5·11 (O1) | S–M | very high |
| A2 | **Candle data-quality validator** (OHLC integrity, gaps, outliers, duplicates, zero volume) stored with the dataset hash | 1·3, 4·22 (O1) | S | very high |
| A3 | **Truncation (look-ahead) test** for every strategy; leakage test suite | 1·3, 4·17, 5·7 (O3) | S | very high |
| A4 | **Sweep robustness report**: mean/median/std, share profitable, neighbour averages, plateau vs peak flag, geometric/log grids, pre-declared ranges | 3·6, 4·21 (O1, O2, O8), 5·9 (O1) | M | very high |
| A5 | **PBO via CSCV** for every sweep | 5·11 (O2) | M | high |
| A6 | **PSR and DSR** (deflated by the ledger count); extended statistics (Sortino, Calmar, Ulcer, time under water, HHI, turnover) | 1·2, 4·23 (O1), 4·21 (O7), 5·14 | M | high |
| A7 | **Locked evaluation segment** (run once) and research-vs-evaluation labelling; boundary purge + embargo on the train/test split | 3·6, 4·21 (O3), 5·7 (O1), 5·11 (O4) | M | high |
| A8 | **Cost ladder / break-even cost**, cost-coverage guard, missed-fill sensitivity | 4·16, 4·21 (O6), 1·5 | S–M | high |
| A9 | **Shock-adjusted backtest report** and outlier review (profit without top-N trades) | 4·21 (O5), 4·22 (O5) | M | high |
| A10 | **Required win-rate / strategy-fragility panel** and bootstrap failure probability | 5·15 | S–M | medium–high |
| A11 | **Synthetic null/test bed** (random walk, O-U, volatility clustering) to validate statistics and give best-of-N null | 5·13 (O1), 3·6 | M | high |
| A12 | Walk-forward analysis with parameter-drift report; later CPCV for sweep-and-pick | 4·21 (O4), 5·12 (O1) | L | medium |
| A13 | Held-out stress periods (2018, Mar 2020, 2022…) | 5·12 (O3) | S–M | medium |

## B. Risk and execution realism

| ID | Item | Where | Effort | Confidence |
|---|---|---|---|---|
| B1 | **Shared volatility toolkit** (true range, ATR, close-to-close σ, Parkinson) | 4·18, 4·20 (O1), 5·19 (O1) | S | very high |
| B2 | **Volatility-based sizing** shared by backtester and live risk module (closes the known sizing gap) | 4·23 (O2), 1·5 | M | very high |
| B3 | **ATR stop mode** and trailing-stop family; maximum-holding (vertical) exit | 4·19 (O2), 4·20 (O2), 4·23 (O4), 5·3 (O2) | M | high |
| B4 | Kelly/half-Kelly ceiling check, risk-of-ruin and binomial advisories | 1·6, 4·23 (O8, O9) | S | high |
| B5 | Volume cap and fill-at-extreme guard; spread-informed slippage table | 1·5, 4·20 (O5), 5·19 (O4) | S–M | medium |
| B6 | Gap-aware sizing; shock detector + crisis-mode **design (needs approval)** | 4·14, 4·22 (O5), 4·23 (O6) | M–L | medium |
| B7 | Paper-vs-backtest parity and expectation sheet | 1·5, 4·22 (O2), 5·1 (O1) | M | high |

## C. Operations and monitoring

| ID | Item | Where | Effort | Confidence |
|---|---|---|---|---|
| C1 | **Alerting / Notifier** (stopped bot, heartbeat, reconcile mismatch, drawdown, data gap) | 1·1 (O1), many | M | very high |
| C2 | Incremental candle import and gap repair | 1·1, 1·3 | S–M | high |
| C3 | Strategy **lifecycle gates** (research → embargo → paper → graduated → re-allocate → decommission) | 5·1 (O1, O2), 4·21 (O9) | M–L | high |
| C4 | Live "model broken?" monitor (drawdown size/duration vs tested distribution) | 4·21 (O9), 4·23 (O8), 5·15 (O4) | M | high |
| C5 | Override log; key-permission policy; continuity runbook | 1·4, 4·22 (O8) | S | medium |

## D. Research hypotheses (each only through the pipeline A; none recommended for direct implementation)

H-PULLBACK-IN-TREND, H-MTF-FILTER, H-VOL-FILTER (eliminate/delay), H-SHOCK-FADE, H-SHOCK-EXIT, H-CUSUM-GATE, H-SADF-REGIME, H-ENTROPY-REGIME, H-DOWN-RUN-BUY, H-PARAM-ENSEMBLE, H-EQUITY-FILTER, H-ILLIQ-FILTER, H-VOLUME-PROFILE; new strategy families: mean reversion (parameterised, with half-life), KAMA trend (book 4 ch. 17), Gustafson down-run rule (4·22).

## E. Diagnostics that support decisions (read-only, low risk)

Efficiency ratio / noise view; sequence and conditional-candle tables with multiple-testing note; calendar (day-of-week/hour) profiles; half-life and mean-reversion tests; volatility clustering; signal outcome table with triple-barrier labels, effective N and component attribution; portfolio view (exposure, correlation, effective number of bets). Sources: 4·1, 4·10, 4·12, 4·15, 5·3, 5·4, 5·8, 5·13, 5·18, 4·24.

## F. Deferred or rejected

| Item | Reason |
|---|---|
| Martingale sizing | Ruin risk; the book's own evidence is mixed (4·22 O6). Anti-Martingale only as capped research. |
| ML meta-labeling filter | Valuable idea (5·3 O3) but requires A1–A7 first; few independent signals per asset; maintenance cost. Decide after A is in place. |
| Dollar/imbalance bars from trades, microstructure features, VPIN | Needs trade-level data and storage; benefit unproven; first run candle-level diagnostics (5·2 O1). |
| Fractional differentiation, entropy features, HRP, mean-variance/genetic allocators | Only relevant with an ML or multi-asset track. |
| Seasonality/cycles/Gann/Fibonacci/chart patterns/VIX systems | Not testable as stated or not applicable to crypto spot. |
| HPC, quantum computing | Not applicable. |

## Suggested order (for discussion, not decided)

1. **Foundation (S–M):** A2, A3, A1, B1, C1.
2. **Honest statistics (M):** A4, A6, A5, A8, A10 — after this, every result carries trials, deflation and overfitting probability.
3. **Realism (M):** B2, A7, B3, B7, A9.
4. **Operations (M–L):** C2, C4, C3.
5. **Research (L):** A11, A12, then D hypotheses one at a time; ML track last.

Decision needed from the owner before any implementation: which of the steps above to approve, and the policy questions flagged in the reports (global exposure caps, crisis mode, lifecycle automation, whether to add ML dependencies).
