---
name: aronson-edge-rationale
description: Why a trading edge might exist and how our own judgment fails, from David Aronson's "Evidence-Based Technical Analysis" ch. 2 and 7 — overconfidence, confirmation bias, illusory correlation (the 2x2 table), false ideas about randomness, theory-backed non-random price motion, limits of the efficient market hypothesis, behavioral finance (limits to arbitrage and rationality), and risk premia that last. Use when proposing a new strategy hypothesis, judging whether a backtested pattern has a plausible reason to persist, or reviewing a discretionary override of a bot.
---

# Edge rationale and cognitive traps (Aronson, *Evidence-Based Technical Analysis*, ch. 2 and 7)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (it does not discuss crypto). Chapter analyses: `docs/books/03-evidence-based-technical-analysis-aronson/ch02-*.md`, `ch07-*.md`. Some philosophy/behavioural sections of the book were only skimmed in those analyses.

## 1. Why subjective chart reading feels valid (ch. 2, pp. 35-101)
- **Overconfidence**: confidence grows with the *amount of information*, not accuracy; agreement among redundant indicators measuring the same thing raises confidence without justification (physicians 88% confident, 20% right; managers 90% confident, 50% right) (pp. 45-46).
- **Second-hand information bias**: a good story persuades more than evidence (pp. 58-61).
- **Confirmation bias**: beliefs filter evidence; chance successes slowly lend credibility to useless methods and **the most experienced users are least able to see their failures** (pp. 62-71).
- **Illusory correlation**: any claim "signal -> outcome" forms a 2x2 contingency table (signal present/absent x outcome yes/no). People overweight the signal-and-outcome cell and neglect false positives, false negatives and true negatives (pp. 72-81).
- **Representativeness / false ideas of randomness**: random series (e.g. 300 coin flips) show apparent patterns; random walks can produce the shapes chartists prize (pp. 93-101).
- Antidote: the scientific method (see `aronson-rule-evaluation`).
**Use**: when a human wants to override or tweak a bot after a few memorable trades, require the 2x2 table over all signals, not the remembered hits.

## 2. Why a pattern needs a theory (ch. 7, pp. 331-385)
- Technical analysis is only justified if prices are non-random to some degree and period, and **each method** still has to prove itself (p. 331).
- A significant backtest **without theory** is an isolated, possibly lucky result; one consistent with sound theory fits a coherent picture. Example: trend in commodity futures as a **risk premium** for taking risk from hedgers. A scientific theory explains several observations and gives **testable predictions** (p. 332).
- Popular justifications fail: "price reflects everything" contradicts the idea that patterns predict prices (and is the premise of the efficient market hypothesis); vague ad hoc stories make no testable predictions; "popular psychology" lacks scientific support (p. 333).

## 3. Efficient markets and their paradoxes (pp. 342-343)
The EMH is questioned by (a) the **smart-vs-fools paradox** (arbitrage needs smart money with more capital, yet efficiency says they do not earn more) and (b) the **cost of information** (nobody would pay for information with no return — Grossman and Stiglitz). Trading costs and short-sale limits prevent full efficiency, so inefficiencies are logically possible.

## 4. Behavioral finance (pp. 355-357, 378)
Two pillars: **limits to arbitrage** (risk, capital, limited patience) and **limits to rationality** (systematic cognitive errors). Prices can **underreact (trends)** or **overreact (reversals)** in predictable circumstances. The EMH attributes deviations to chance and short life; behavioral finance claims systematic deviations that last long enough to exploit. The author notes it is not yet known which specific hypotheses are right.

## 5. Non-randomness consistent with efficiency: risk premia (pp. 378-385)
Differences in risk aversion create premia: **equity premium**; **hedging premium in commodities/currencies** (trend followers profit); **liquidity premium** (short-term gains from buying recent weakness: contrarian strategies); **information / price-discovery premium**. Premia tend to last longer than true inefficiencies, which are ephemeral; taking risk indiscriminately earns no premium. Technical signals can be read as "advertisements" for demand for risk or liquidity.

## 6. [Adaptation] Hypothesis template for a bot idea
For each strategy proposal write, before any backtest:
1. **Who is on the other side and why do they lose?** (forced liquidations, funding-driven crowding, slow information, hedging demand, liquidity provision). If no answer, treat the idea as a search over noise.
2. **Which premium or behavioral mechanism does it harvest**, and does it persist or is it ephemeral?
3. **A testable prediction on unseen data** and the result that would falsify it.
4. **Capacity/competition**: with <= 1000 USDT capacity is not binding, but speed against HFT/arbitrage may be.
5. The 2x2 table of signals vs outcomes over the *whole* sample (including quiet periods), not only highlighted trades.
Crypto-specific mechanisms to test (not claims from the book): liquidation cascades, funding-rate extremes, basis, retail herding, exchange-listing effects. Treat each as a hypothesis with its own falsifier.
