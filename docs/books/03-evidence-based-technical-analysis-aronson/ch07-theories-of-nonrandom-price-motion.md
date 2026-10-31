# Book 3 · Chapter 7 — Theories of Nonrandom Price Motion

*Evidence-Based Technical Analysis*, Aronson (2007). Book pages (PDF = book + 16; OCR scan). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 331–333, 342–343, 355–357 and 378–385 were read in full. The long middle sections (pp. 334–341 random walk and efficient-market evidence, 344–354 further critique, 359–377 specific behavioural biases and their predicted price patterns) were read by heading only and are **not summarised in detail**. This is a theory chapter with little operational content for the code.

## 1. Chapter summary

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | TA is justified only if price movements are nonrandom to some degree some of the time; even then each *method* must prove itself with evidence. | Premise of the whole book. | 331 |
| C2 | **Why theory matters**: a significant back test without theory is an isolated, possibly lucky result; a back test consistent with sound theory is "part of a larger cohesive picture". Example: trend-following in commodity futures as a **risk premium** for transferring risk from hedgers. A scientific theory explains many observations and makes **testable predictions**. | Distinguishing flukes from effects. | 332 |
| C3 | **Critique of popular TA theory**: "price reflects everything" contradicts the idea that patterns predict (and is the premise of its enemy, EMH); vague, ad-hoc rationales give no testable predictions; "pop psychology" lacks scientific support. | Bad justifications. | 333 |
| C4 | **Efficient-market hypothesis (EMH) is challenged by its own paradoxes**: *smart versus dumb* (arbitrage needs the smart to have more capital, yet efficiency says smart earn no more), *cost of information* (no one would pay to gather information that earns nothing: Grossman & Stiglitz). Costs of trading and short-sale limits keep markets from full efficiency. | Why inefficiencies are logically necessary. | 342–343 |
| C5 | **Behavioural finance** as a theory of nonrandom price motion: two pillars, **limits of arbitrage** (risk, capital, limited patience) and **limits of rationality** (systematic cognitive errors); prices *under-react* (trends) or *over-react* (reversals) in predictable circumstances; EMH says departures are random and brief, behavioural finance says some are systematic and last long enough to exploit. The author notes it is not yet clear which specific hypotheses are correct. | Mechanisms behind trends and reversals. | 355–357, 378 |
| C6 | **Nonrandom motion can coexist with efficiency**: investors differ in risk attitudes, so **risk premiums** exist: equity premium; **commodity/currency hedging premium** (profitable trends for trend followers); **liquidity premium** (short-term gains for buying recent weakness: countertrend strategies); **information/price-discovery premium**. Premiums "are more likely to endure" than true inefficiencies, which are ephemeral; a careless risk-taker does not collect. TA signals can be read as "want ads" for risk or liquidity. | What makes an edge durable. | 378–385 |

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| Rationale for each strategy | ⚠️ | Docstrings state the mechanical rule (`ema_crossover.py`, `donchian_breakout.py`) and the catalogue has `DESCRIPTION` strings, but there is no stated *economic or behavioural mechanism*, no falsifiable prediction, and no known failure regime. |
| Testable predictions tied to a mechanism | ❌ | None recorded; diagnostics (book 2 ch. 2 and 6) would be the place. |
| Premium vs inefficiency classification | ❌ | n/a. |
| Awareness of crypto-specific structure | ❌ | Not in the system or docs. |

## 3. Opportunities

### O1 — A "thesis" block for every strategy: mechanism, prediction, failure regime *(book: C2, C3, C6, pp. 332–333, 378–385)*
* **Problem:** strategies are described by what they do, not by why they should work, so a good back test is an isolated result (the book's complaint) and there is no criterion for retiring a strategy when its mechanism changes.
* **Proposal:** extend strategy metadata (`catalog.py` / `base.py`) with: (a) the hypothesised mechanism (for example "under-reaction and herding generate trends over N hours"; "liquidity provision after forced selling generates reversals"), (b) an *observable prediction* that would falsify it, tied to a diagnostic (autocorrelation of returns at the strategy's horizon, book 2 ch. 6 O1; half-life, book 2 ch. 2 O1), (c) whether it is a **risk/liquidity premium** (more durable) or an exploitable inefficiency (ephemeral), and (d) conditions under which it should fail. Show it in the app next to the parameters and next to results.
* **Benefit:** ties research to testable claims, supports the post-mortem notes (book 2 ch. 4 O1) and hypothesis pre-registration (book 3 ch. 2 O3, ch. 3 O3). **Complexity:** low (metadata + UI). **Risk:** the text can become decoration; the benefit appears only if the prediction is actually checked by a diagnostic. **Validation:** every registered strategy must provide the block (a unit test over the registry).
* The crypto content of mechanisms is **our proposal**; the book supplies the framework (risk premiums, under- and over-reaction, limits of arbitrage), not crypto evidence.

### O2 — Diagnostic that checks the strategy's own prediction *(book: C2, p. 332)*
Implement the diagnostics that O1 references (autocorrelation/half-life at the strategy's timeframe, trend persistence after volume or volatility shocks as a candidate) and show a pass/fail/inconclusive status per pair and timeframe. This depends on book 2 ch. 2 O1 and ch. 6 O1; no separate work. **Complexity:** depends on those items.

### O3 — Plan for edge durability *(book: C6, p. 380 · adaptation)*
Record, for each deployed bot, whether its thesis is a premium or an inefficiency and set review intervals: ephemeral ones need shorter monitoring windows (decay monitor, book 2 ch. 4 O1). **Complexity:** low. **Risk:** subjective classification.

### Not applicable
EMH debate, random-walk evidence, particular behavioural biases (not read in detail), equity-factor models.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 thesis metadata | medium | medium | – | low | – |
| 2 | O2 prediction check | high | – | – | per dependency | book 2 ch. 2/6 |
| 3 | O3 durability review | – | medium | – | low | decay monitor |

## 5. Affected files
`strategies/domain/base.py`, `strategies/catalog.py`, `strategies/presentation/` (schema), `docs/openapi.json`, app strategy pages and `lib/shared/strategies`, `check:consistency`, tests over the registry.

## 6. Incremental plan
1. Add the metadata fields and fill them for the two existing strategies.
2. Display in the app.
3. Link O2 diagnostics as they appear.

## 7. Acceptance criteria and tests
* Every registered strategy exposes mechanism, prediction and failure-regime text; a test fails if one is missing.
* No change to strategy behaviour; ruff, mypy and tests green.

## Caveats
Theories explain and constrain; they do not guarantee. The book itself says it is unclear which behavioural hypotheses are right (p. 378). Much of the chapter (the detailed behavioural and EMH material) was not read in detail.
