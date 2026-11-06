---
name: aronson-rule-evaluation
description: How to evaluate a trading rule objectively, from David Aronson's "Evidence-Based Technical Analysis" ch. 1, 3, 4 — objective (codable) rules, null hypothesis, benchmark with no predictive power, removing market trend and position bias via detrended returns, next-bar execution to avoid look-ahead, traditional plus inverse rules. Use when defining a bot entry/exit rule, writing the backtest return calculation, or deciding whether a backtest return is skill or just market drift/long bias.
---

# Objective rule evaluation (Aronson, *Evidence-Based Technical Analysis*)

Page numbers are book pages (the PDF is the book + 16 pages; OCR scan). **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (it studies S&P 500 daily rules and says nothing about crypto). Chapter analyses: `docs/books/03-evidence-based-technical-analysis-aronson/ch01-*.md`, `ch03-*.md`, `ch04-*.md`. Follow with `aronson-significance-tests` and `aronson-data-mining-bias`.

## 1. A rule must be testable (pp. 2-7, 144-148)
- A claim needs **cognitive content**: it must be possible to tell whether it is right or wrong. Objective = **programmable** into unambiguous positions; subjective methods (chart patterns, Elliott waves) are not testable.
- Hypothetico-deductive method: observation -> hypothesis (the pattern is not a sample artifact) -> conditional prediction on **new** data -> verification -> statistical inference. A profitable backtest does **not** prove the hypothesis (affirming the consequent); an unprofitable one can refute it. So state a **null hypothesis** (the rule earns nothing) and try to reject it.
- First explanations of a great result: **sampling luck** and **data-mining bias** — rule them out before accepting predictive power (pp. 146-147).
- Four classes: subjective; objective of unknown significance; objective, tested, **not significant** (probably the majority, as in every science); objective and significant. What matters is a procedure to **discard** what does not work (pp. 161-163).

## 2. Define the rule formally (pp. 16-22)
A rule maps an input series to positions (+1 long, -1 short, or 0). Aronson's case study uses **binary always-in-the-market rules**. Thresholds can be fixed or variable (moving average, bands) and may use flip-flop logic (two events). **Test the traditional interpretation and its inverse** — the conventional reading may be wrong, or the input may have no obvious reading (pp. 21-22).

## 3. Benchmark and the position-bias trap (pp. 22-29)
- The benchmark is a **rule with no predictive power** (a placebo), not zero and not necessarily buy-and-hold.
- Backtest return = predictive component + unwanted component from (1) the fraction of time long vs short and (2) the market's average daily change in the sample. A random rule's expected return: `ER = p(L) * ADC - p(S) * ADC`. Example (S&P 500, 1976-2004, ADC +0.035%/day = 9.22%/yr): a random rule long 90% of the time earns ~7.31%/yr and long 60% earns ~1.78%/yr **with zero predictive power** (pp. 23-27). Asymmetric buy/sell conditions create such bias.
- **Fix**: evaluate on **detrended** market returns — subtract the sample mean daily return — which is equivalent to subtracting the placebo's expected return (proof in the appendix). Use detrended data only to compute rule returns; signals still use real prices. Use **log returns** `ln(P_t / P_t-1)` (pp. 27-29).

## 4. Look-ahead and execution (pp. 29-31)
If the signal uses the close, the earliest execution is the **next open**: daily rule return = position at close of day 0 x `ln(Open_t+2 / Open_t+1)` minus the mean log return. Lagged or revised inputs must also be lagged. Trading costs are needed when a rule stands alone; the author omits them in his case study because he looks for predictive information (p. 31) — we cannot omit them for a bot.

## 5. [Adaptation] For perpetual-futures bots
1. Backtests report **detrended excess return** next to raw return, plus the fraction of time long/short. A long-biased rule in a rising sample is not skill; crypto drift over a window can be huge, so the correction matters more than in equities.
2. Funding paid/received depends on position side and time-in-market; treat it as a separate cost line, not part of the signal's merit.
3. Signals computed on a candle become tradable at the **next candle's open** (the forming candle is not usable); this mirrors the book's rule.
4. Every rule is registered with its **inverse** and with a no-edge placebo (random positions with the same long/short fraction) so the result can be compared with luck.
5. Keep flat/neutral states explicit: the book's always-in-market design simplifies statistics; if a bot has a flat state, the placebo must reproduce the same time-in-market.

## Checklist
- [ ] Rule is fully programmable; hypothesis and null stated beforehand.
- [ ] Execution lag respected; log returns used.
- [ ] Returns detrended / benchmarked against the placebo with the same position mix.
- [ ] Inverse rule evaluated.
- [ ] Costs and funding included for any deployable result.
- [ ] Next: significance (`aronson-significance-tests`) and selection-bias correction (`aronson-data-mining-bias`).
Historical results are examples, not guarantees of future returns.
