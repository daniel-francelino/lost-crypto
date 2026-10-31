# Book 4 · Chapter 11 — Cycle Analysis

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 485–489 were read. The methods sections — uncovering the cycle (Fourier/spectral analysis, trigonometric fitting), maximum entropy (MESA), the cycle channel index, the short-cycle indicator and phasing (pp. 494–526) — were scanned by heading only and are **not** summarised. Appendix 3 (trigonometric regression) was not read.

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | The **cycle** is one of the three orderly components of price (trend, seasonality, cycle; the fourth is noise). Types: seasonal, production start-up/shutdown, inventory, behavioural, astronomical, presidential-election. Cycles can be periodic (regular interval) or regular in amplitude but irregular in period. The common methods are trigonometric curve fitting and Fourier/spectral analysis; Ehlers' maximum-entropy method works with little data. Short-term cycles are attributed to behaviour (covered in ch. 15). | 485 |
| C2 | To isolate a component remove the others: first differences remove the trend; subtracting a one-year average (or the value 252 days ago) removes the seasonal pattern, leaving cycle and noise. The 20-business-day reference corresponds to a lunar month and four weeks. Cycles are often sums of sub-cycles with harmonic relations; any series can be decomposed into cycles. | 486 |
| C3 | **Before analysing, observe that a dominant cycle exists and know why it exists, to avoid spurious patterns**: fundamental or industrial reasons (inventory, breeding and feeding time, mine closure and restart, interest-rate policy). Example: a clear 9–11 month **cattle cycle** (peaks vary by up to a month, about 20% variance) with a production reason; the **Swiss franc cycle** has a sub-cycle of 24–35 weeks (40% variance), no specific fundamental cause, and "these patterns do not need to be rigid". | 486–487 |

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| Spectral/cycle analysis | ❌ | No Fourier, MESA or cycle code. |
| Requirement of a causal reason for a pattern | ❌ (process) | See book 3 ch. 7 O1 (thesis block). |
| Cycle-based strategies | ❌ | None. |

## 3. Opportunities

### O1 — Apply the "reason first" rule to any cycle idea; do not build spectral tools yet *(book: C3, p. 486)*
The most reusable message is methodological: a cycle without a causal story is probably spurious. Crypto folklore proposes multi-year cycles (for example around supply-halving events), but the available history contains only a handful of cycles, which gives almost no statistical power; the book's cycles have 20–40% period variance even in well-understood markets. **Recommendation:** do not implement cycle detection now. If a cycle hypothesis is wanted, register it as a hypothesis with its mechanism and its falsifying prediction (book 3 ch. 7 O1) and test it only with the evidence pipeline, counting every cycle length tried in N. Record as **H-CYCLES**. **Complexity if ever built:** medium–high (spectral estimation in pure functions).

### O2 — Detrend/de-seasonalise before looking for structure *(book: C2, p. 486)*
When the diagnostics module (calendar effects, book 4 ch. 10 O1) grows, subtract the mean/trend first (first differences or return series) as the book describes, so the trend does not mask other components. Already part of those items.

### Not applicable
Astronomical cycles, presidential cycles, cattle and currency specifics, MESA and Fourier implementation (not read).

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 hypothesis rule | – | – | – | none | thesis block |
| 2 | O2 detrending note | – | – | – | trivial | diagnostics |

## 5–7. Files, plan, acceptance
No code. Documentation only: add the "reason first" rule to the strategy-thesis guidelines.

## Caveats
The cattle and Swiss franc examples are 1980–2002 futures observations from charts; no statistical significance is reported in the pages read. Nothing here supports the existence of crypto cycles.
