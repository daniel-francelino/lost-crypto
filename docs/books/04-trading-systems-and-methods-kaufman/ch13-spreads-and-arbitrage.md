# Book 4 · Chapter 13 — Spreads and Arbitrage

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 565–568, 572–574 and 596–598 were read; the headings of 568–572 and 574–616 were scanned. The detailed spread mechanics for specific futures markets, option-related arbitrage, pricing formulas and intermarket spread studies (pp. 568–572, 575–595, 598–616) were **not** read in detail and are not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Terms: **spread/straddle** (opposite positions in related markets), **pairs trading** (long/short in two stocks), **arbitrage** (the dynamics of the spread can be calculated, e.g. same bond, same maturity, or one commodity in two locations); **relative-value arbitrage** when divergence is caused by market forces on similar but not identical products. Spreads remove directional risk (both legs move together; one profits, the other loses) and offer diversification from long-only portfolios. | 565 |
| C2 | Futures intramarket spreads reduce risk and profit; margin offsets allow leverage, **unlike stocks where both legs need full financing**. Behaviour differs by market: financial near-delivery contracts react faster, precious metals follow carry, industrial metals invert in tight supply, currency forwards reflect interest differentials and policy, crops have carry within a crop year, livestock has no storage so months are independent. | 566–567 |
| C3 | **Carrying charge** (term structure): interest, storage, insurance; **contango** vs **backwardation** (negative carry) — the carry is implicit even when inverted. | 567 |
| C4 | **Spread relationship test**: compute the standard deviation of the spread's returns relative to the legs; "the stronger the relationship between A and B, the smaller the standard deviation of F". | 572 |
| C5 | **Arbitrage conditions** (spatial arbitrage example: peso quoted by banks in Tokyo and Frankfurt): the price difference must exceed the bid–ask spread (execution cost); credit must exist with both counterparties; the two transactions must be **simultaneous**; large-scale arbitrage is the domain of institutions that scan quotes globally and trade large quantities for small differences; opportunities that are true arbitrage have small profits and low liquidity; risk grows with time in the trade. | 572 |
| C6 | **Futures pricing**: convenience yield `CY = F − S − S·r·(T−t)/365` (gold example 1.20% over six months); fair-value range bounded by financing, storage and convenience cost, widened by separate borrowing/lending rates and transaction costs; outside the range → arbitrage. | 573–574 |
| C7 | **Carry trade**: borrow low-yield currency, buy high-yield; executed through forwards/futures, so it relies on **forward bias** (high-yield currencies tend to appreciate or fall less), not on harvesting the carry directly; the main risk is a currency move offsetting the interest gain; diversification across currencies is needed. | 596–597 |

This chapter is about instruments the project does not trade; the ideas touch crypto in four places. Crypto remarks are **our adaptation**.

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| Spreads / pairs | ❌ n/a | One asset, long-only, no short leg. |
| Cross-exchange or triangular arbitrage | ❌ n/a | One exchange adapter per connection; no simultaneous two-leg execution or inter-exchange balance management. |
| Carry (funding rate, basis) | ❌ n/a | No derivatives. |
| Cost test before acting on a price difference | ✅ in spirit | Fee and slippage are always included in simulations. |

## 3. Opportunities

### O1 — Record the arbitrage conditions as a screening checklist, and keep crypto arbitrage out of scope *(book: C5, p. 572 · adaptation)*
The author's conditions for a real arbitrage (difference larger than the bid–ask spread, credit/access to both counterparties, simultaneous execution) map onto the practical facts of crypto: withdrawal/transfer delays and fees between exchanges, fee tiers, rate limits, and non-atomic order placement. A retail single-account system without co-location is unlikely to capture them. **Decision recommended: not to pursue cross-exchange or triangular arbitrage**; write the checklist into the strategy-idea template so any such idea must show how each condition is met. **Complexity:** documentation only.

### O2 — Funding-rate / basis carry as a *data point* for a future derivatives decision *(book: C3, C7, pp. 567, 596–597 · speculative)*
If perpetual futures were ever supported (**B-DERIVATIVES**, book 2 ch. 5 O3), the carry-trade discussion (including the point that the forward already discounts the interest differential and profits rely on forward bias) is the right framing, along with the risk that spot moves can overwhelm carry. No work now.

### O3 — Relationship check between two instruments before any pair-like idea *(book: C4, p. 572)*
For a research report that compares two symbols (for example an alt against BTC), use the book's quick test: standard deviation of the ratio/difference returns vs the legs'. This is a cheap addition to the diagnostics module (book 2 ch. 2 O1) and a prerequisite for any `companion_symbol` work (H-COMPANION, book 3 ch. 8 O5). **Complexity:** very low.

### Not applicable
Commodity carrying-charge mechanics, convenience yield calculations, interest-rate parity, currency carry execution, calendar spreads.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 checklist and decision | – | medium | – | doc | – |
| 2 | O3 relationship check | low | – | – | very low | diagnostics |
| 3 | O2 carry framing | – | – | – | none | derivatives decision |

## 5–7. Files, plan, acceptance
Documentation (`docs/`) and, for O3, a pure function in `analytics/domain`; no trading changes. Acceptance: O3 returns the standard-deviation ratio on fixtures; ruff, mypy, tests green.

## Caveats
Most of the chapter concerns futures and institutional arbitrage and was not read in detail. Nothing in the pages read supports retail crypto arbitrage; the recommendation not to pursue it rests on the conditions the author states, not on measured crypto data.
