---
name: aronson-data-mining-bias
description: Data-mining (selection) bias and how to correct it, from David Aronson's "Evidence-Based Technical Analysis" ch. 6, 8-9 — best-of-N null distribution, the five factors that drive the bias, out-of-sample and walk-forward remedies, Markowitz-Xu shrinkage, White's Reality Check and Monte Carlo permutation for best-of-N, the 6,402-rule case study (best rule 10.25%/yr, corrected p = 0.82), and the train/test/validation scheme for adding complexity. Use whenever a bot strategy was chosen from a parameter sweep or many variants, when reporting sweep results, or when deciding how many trials to count.
---

# Data-mining bias (Aronson, *Evidence-Based Technical Analysis*, ch. 6, 8, 9)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (S&P 500 daily rules only). Chapter analyses: `docs/books/03-evidence-based-technical-analysis-aronson/ch06-*.md` (the book's most relevant chapter for our parameter sweep), `ch08-*.md`, `ch09-*.md`. See also `quant-research` (deflated Sharpe) and `walk-forward-validation`.

## 1. The problem (pp. 255-284)
Data mining = multiple comparison: define the problem, the rule universe and a metric, then pick the best observed result. The chosen rule tends to be best in the future too (White), **but its observed performance is an upward-biased estimate of its expected performance.** Using the same number both to select and to estimate is "the data miner's mistake". Most of the post-selection decline out of sample is **regression of a lucky pick to the mean**, not necessarily market change (pp. 262-272). Single-rule backtest: the average is an unbiased estimate (pp. 268-272).
Search types: **parameter optimization** (narrowest), **rule search** (different forms), **rule induction** (variable complexity; machine learning) — all biased (pp. 264-267).

## 2. Wrong vs right null (pp. 171-172, 275-278)
Comparing the best rule with the null of a **single** rule is wrong. The right null is the distribution of the **maximum of N** useless rules, centered well above zero (book illustration: for 50 useless rules the best-mean distribution is centered at +33%; an observed +37% has p ~ 0.45, not < 0.05). The more luck relative to merit (typical in markets), the larger the bias (pp. 278-284).

## 3. Five factors determine the bias (pp. 287-291, 318-320)
1. **Number of rules tested** — more rules, more bias (grows with log N).
2. **Number of observations** — more observations, less bias.
3. **Correlation among rule returns** — the less correlated, the larger the bias (correlated rules are fewer effective trials).
4. **Positive outliers** — large positive returns raise the bias; more observations dilute it.
5. **Variation in true merit among rules** — the more similar the merit, the larger the bias.
These describe the **mean return** statistic; other metrics (Sharpe) may behave differently.

## 4. Remedies (pp. 320-330)
- **Out-of-sample test**: unbiased, but data lose their "virgin" status once used and research data shrink. Schemes: initial/final split, checkerboard, **walk-forward** with rolling windows and non-overlapping test segments (independent estimates and a confidence interval).
- **Markowitz-Xu correction**: shrink the best rule toward the average of all rules, `H' = R + B * (H - R)`, `B` between 0 and 1 (needs interval returns of all rules). "Can work surprisingly well, but can also fail badly" — a rough guide only.
- **Randomization tests for the best of N**:
  - **White's Reality Check (bootstrap)**: store per-interval returns of every rule; resample **dates** with replacement (same dates for all rules); center each rule at zero; take the **largest mean** per resample; repeat >= 500 (the book also uses 5,000 elsewhere); p = fraction of maxima >= best observed. Patented (per the author).
  - **Monte Carlo permutation (Masters)**: keep each rule's signal sequence and pair it with the **same shuffled market changes** for all rules (preserving correlation among rules); take the largest mean; repeat.
  - Both lose power if the universe includes rules **worse than useless** (Hansen), e.g. inverse rules. Romano-Wolf improvements address this.
- **Practical requirement**: **save the per-interval returns of every rule tested** — "few data miners keep that information" (p. 327).

## 5. Case study results (pp. 389-448)
- 6,402 rules on the S&P 500, Nov 1980 - Jul 2005 (channel breakouts, extremes/transitions, divergences; binary +/-1; includes inverse rules); published rules from others were deliberately excluded because their search history is unknown (pp. 390-391).
- Parameter grid: 11 windows in roughly **geometric progression, ratio ~1.5** (3, 5, 8, 12, 18, 27, 41, 61, 91, 137, 205 days); 858 trend rules = 39 entries x 11 windows x (traditional + inverse) (pp. 419-420).
- **Result: none of the 6,402 rules was significant at 0.05 after correction.** Best rule 10.25%/yr on detrended data, corrected p = **0.8164** (bootstrap) and **0.8194** (permutation) (pp. 441-442).
- The best of N useless rules is expected to earn ~**11%/yr** here; ~15% would be significant at 0.05 and ~17% highly significant (pp. 442-443).
- A naive single-rule test gave p = 0.0005 for the best rule, and ~320 of 6,402 rules (~5%) looked significant at 0.05 — exactly the chance expectation (pp. 443-444).
- Confidence intervals that account for selection are **joint** (80%) for all rules; best rule: -2.9% to +23.5% (pp. 444-448).
- Design checklist the author applies: no-skill benchmark, market-trend removal, next-bar execution, selection-bias control, no peeking (pp. 448-449).

## 6. Adding complexity: train/test/validation (pp. 457-461)
Train fits parameters at a given complexity; the **test** segment decides when to stop adding complexity (stop when test performance peaks and worsens); an untouched **validation** segment gives the only unbiased estimate (test results are biased by repeated queries). Walk-forward can slide the three-segment window. Example: MA crossover with 2 parameters (30% train / 15% test); add an RSI filter (4 parameters; 50% / 20%); continue until test falls. No robust significance test existed in 2007 for machine-induced nonlinear rules (pp. 455-457).

## 7. [Adaptation] Rules for the bots
1. Every sweep logs **per-bar returns for every variant** (the "trial register"); without it no best-of-N test is possible. Count parameters x variants x symbols x timeframes x entry/exit styles as trials.
2. Report sweep winners with a best-of-N p-value (permutation or Reality-Check-style) and the shrunken estimate, **never** the raw best number alone.
3. Prefer **plateaus**: neighboring parameters should perform similarly; use a geometric grid to avoid redundant near-duplicates.
4. Keep an untouched validation window (most recent months) and walk-forward; once looked at, it is burned.
5. Correlated variants (same family, neighboring parameters) count as fewer effective trials, but do not assume independence — err conservative.
6. Include inverse rules in the universe only if the test handles worse-than-useless rules (Hansen), otherwise note the loss of power.
7. Sample sizes: crypto bars are dependent; the effective sample is much smaller than the bar count.
No result here guarantees future returns.
