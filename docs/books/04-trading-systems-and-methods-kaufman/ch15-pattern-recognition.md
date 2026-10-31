# Book 4 · Chapter 15 — Pattern Recognition

*Trading Systems and Methods*, 5th ed., Kaufman (2013). Book pages (PDF = book + 20). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 685–692 and 732–734 were read, plus the first lines of p. 732. The pivot-point/DeMark projections (688), intraday timing detail (692–698), opening gaps (699–710), weekday/weekend/reversal tables (711–731; large tables of sequence frequencies) and the AI methods (735–736) were **not** read in detail and are not summarised.

## 1. Chapter summary (pages read)

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Pattern recognition underlies most systems; much early pattern knowledge is **lore** ("up Monday, down Tuesday", "locals even-up on Fridays", "watch for key reversals") worth testing by computer. **Sequence tally method**: record all 2-day (4), 3-day (8), 4-day (16)… up/down patterns and measure the frequency of the next move to see whether a pattern predicts; "a source of many valuable ideas as well as false paths". | Testing folklore objectively. | 685–686 |
| C2 | Statisticians say the best forecast of tomorrow is today's price (long-term: the mean); yet traders project daily ranges: **pivot points** `P = (H+L+C)/3`, `R1 = 2P − L`, `S1 = 2P − H`, `R2`, `S2`; DeMark's projected ranges condition on the open relative to the previous close. | Level projections. | 687–688 |
| C3 | **Time of day**: the classic intraday volume shape (highest near the open, next near the close, lowest midday); habits (evening analysis → morning orders; closing prices for settlement; institutions trade when volume is heavy or use VWAP orders; lunch-time liquidity lull may cause a temporary reversal). Market structure has not altered the time patterns despite high-frequency trading. | Intraday seasonality. | 689–690 |
| C4 | **Tubbs' six intraday patterns** (e.g. a rally returning to the opening price by 1 pm implies a weaker close); anecdotal rules from tape reading. | Lore. | 690 |
| C5 | **Reversal-day statistics** (S&P): after a higher-high/lower-close day, the next open continues lower 52% of the time but the next close only 43% lower (opening reversal not sustained; rally open-to-close); after a lower-low/higher-close day only 40% higher open but 53% higher close; the author notes these exceed the general upward bias of equity indices; markets differ (wheat, crude oil show other patterns). | Conditional next-day behaviour. | 731–732 |
| C6 | **Computer-based pattern recognition via trade profiles** (Aronson's earlier method): define the *outcome* you want (price moves ≥3% within 20 days without a loss over 0.5%); mark the 5 days before each such move as "buy days" (and the symmetric "sell days"); then search indicators (moving-average direction, RSI or sentiment, volume direction, 10-day momentum) for **combinations that occur mostly on those days**; the ideal signal has no losing signals in the zone, which does not exist in practice, so signals must still be judged by net return and risk. Analogous to the multiple regression approach. | Labelling outcomes and discovering predictors. | 732–734 |

Crypto remarks are **our adaptation**.

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Up/down sequence statistics | ❌ | None. |
| Time-of-day / weekday statistics | ❌ | None (planned in book 4 ch. 10 O1). |
| Reversal-day conditional statistics | ❌ | None. |
| Outcome labelling for supervised learning | ❌ | No labels, features or ML module. This is the topic of book 5. |
| Pivot-point style level projections | ❌ | None; not recommended without evidence. |

## 3. Opportunities

### O1 — N-candle sequence diagnostics (conditional probabilities of the next candle) *(book: C1, pp. 685–686)*
* **Proposal:** in the series-diagnostics module, tabulate for `k = 2…5` the frequency of up/down candle sequences and the conditional probability that the next candle's return is positive (and its mean), with sample sizes, an unconditional baseline, and a **correction count** (the number of patterns examined: 2+4+8+16 = 30 tables for k up to 4 plus further for the next-move definitions), reporting results as the book's "ideas and false paths": a screening aid only.
* **Benefit:** a quick objective answer to "does any short sequence predict direction on this pair/timeframe?". **Complexity:** low. **Risks:** huge multiple-testing risk; autocorrelation and volatility clustering make runs look informative; weak edges disappear after costs; do not turn into a strategy without best-of-N and validation (book 3). **Validation:** synthetic random walk should yield about 5% of tables "significant" at p = 0.05 before correction.

### O2 — Reversal-day and opening-gap studies are the same diagnostics with different conditioning *(book: C5, p. 731–732)*
Add conditioning by *prior-candle type* (outside/inside, higher high with lower close, etc.) to O1's tables and report the open-to-close behaviour of the next period. Equity-index results in the book show that conditional behaviour can differ strongly from the unconditional drift. For crypto, "next open" is simply the next candle's open (no gap); the hypothesis is about candle-to-candle persistence. **Complexity:** low. Same multiple-testing caution.

### O3 — Outcome labelling pipeline (bridge to book 5) *(book: C6, pp. 732–734)*
The method defined by "a move of at least x% within n days without an adverse move beyond y%" is a **barrier-style label**; marking the days before such moves and searching for indicators that discriminate them is supervised learning in plain language. It anticipates the labelling methods in López de Prado (triple barrier, meta-labelling), to be analysed in [book 5](../05-advances-in-financial-ml-lopez-de-prado). Do not build anything here; the design belongs to that analysis (leakage, overlapping labels, purged cross-validation).

### O4 — Intraday volume/time shape as a feature, not a rule *(book: C3, p. 689–690 · adaptation)*
Use hour-of-day normalisation of volume and volatility (book 4 ch. 12 O1) rather than rules such as "if the rally returns to the open by 1 pm…", which rest on equity session structure that crypto spot lacks. **Complexity:** part of ch. 12 O1.

### Not applicable
Pivot-point and DeMark projections (no evidence provided), Tubbs' tape-reading patterns, equity open/close structure.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 sequence diagnostics | low | – | – | low | diagnostics module |
| 2 | O2 conditional next-candle tables | low | – | – | low | O1 |
| 3 | O3 labelling bridge | – | – | – | – | book 5 analysis |
| 4 | O4 time/volume features | low | – | – | low | ch. 12 O1 |

## 5. Affected files
`analytics/domain/` (sequence and conditional tabulation), diagnostics endpoint, app diagnostics page, tests.

## 6. Incremental plan
1. Tabulation functions and the correction count.
2. Report in the app with null-baseline comparison.
3. Plan labelling after book 5.

## 7. Acceptance criteria and tests
* On synthetic random-walk data about 5% of cells exceed p = 0.05 uncorrected; with a planted dependency the cell is flagged; all read-only; ruff, mypy, tests green.

## Caveats
The statistics cited come from futures and equity indices (often 1980s–2000s); some are described as "interesting" without tests of significance. Ideas from this chapter are search hypotheses, not evidence.
