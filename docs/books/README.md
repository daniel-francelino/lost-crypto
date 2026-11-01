# Book analyses

Chapter-by-chapter analyses of the reference books in [`books/`](../../books), compared with the real Lost Crypto code. Method and rules: [`books/prompt.txt`](../../books/prompt.txt).

**Rules that apply to every report**

* Analysis only. Nothing here has been implemented; implementation starts after the owner approves a plan.
* Book claims carry **book page numbers**. Where the book's text did not support something, the report says it is *our adaptation* (crypto is never discussed by these books unless stated).
* Code claims were checked in the repository on the date of [00-system-baseline](00-system-baseline.md). Update that file when the code changes.
* Historical results quoted from the books are the authors' examples, not evidence of future returns.
* Page numbers: the PDF page equals the book page plus an offset noted at the top of each report.

## Status

| # | Book | Chapters | Status |
|---|---|---|---|
| 1 | Chan, *Quantitative Trading* (2009) | 8 | ✅ done, see [folder](01-quantitative-trading-chan) |
| 2 | Chan, *Algorithmic Trading: Winning Strategies and Their Rationale* (2013) | 8 + conclusion | ✅ done, see [folder](02-algorithmic-trading-chan) |
| 3 | Aronson, *Evidence-Based Technical Analysis* (2007) | Intro + 9 | ✅ done (some philosophy/behavioural sections skimmed, see each report), see [folder](03-evidence-based-technical-analysis-aronson) |
| 4 | Kaufman, *Trading Systems and Methods* (5th ed., 2013) | 24 (appendices not analysed) | ✅ done (reading depth declared in each report; ch. 3–6, 10–15, 18 only partly read), see [folder](04-trading-systems-and-methods-kaufman) |
| 5 | López de Prado, *Advances in Financial Machine Learning* (2018) | 22 (ch. 20–22 grouped) | ✅ done (ch. 18, 19, 20–22 and parts of 8, 16, 17 only skimmed), see [folder](05-advances-in-financial-ml-lopez-de-prado) |

## Book 1 reports

| Chapter | Report | Main outcome |
|---|---|---|
| 1 | [Whats, Whos, Whys](01-quantitative-trading-chan/ch01-whats-whos-whys.md) | No alerting channel exists (O1); manual-import gaps; intervention reasons |
| 2 | [Fishing for Ideas](01-quantitative-trading-chan/ch02-fishing-for-ideas.md) | ✅ Implemented: risk ratios, drawdown duration, cost ladder, periods, screening, sweep trials and train-based ranking |
| 3 | [Backtesting](01-quantitative-trading-chan/ch03-backtesting.md) | ✅ Implemented: truncation test, candle integrity + outliers, gap guard, data quality per run, sweep robustness, listing snapshots (O1/O2/O9 via ch. 2) |
| 4 | [Setting Up Your Business](01-quantitative-trading-chan/ch04-setting-up-your-business.md) | ✅ Implemented: daily key re-checks with visible reason, exposed-position report, external worker health, tested backups, clock-skew guard, runbook |
| 5 | [Execution Systems](01-quantitative-trading-chan/ch05-execution-systems.md) | ✅ Implemented: execution record (slippage, latency), stored bot candles, bot vs backtest parity (gates live), backtests timed and sized like the bot, volume cap, divergence checklist |
| 6 | [Money and Risk Management](01-quantitative-trading-chan/ch06-money-and-risk-management.md) | Kelly reference as advice; tail-aware exposure cap; only hard pauses, no gradual de-risking |
| 7 | [Special Topics](01-quantitative-trading-chan/ch07-special-topics.md) | Only trend strategies; no time exit; half-life tool; data cleansing first |
| 8 | [Conclusion](01-quantitative-trading-chan/ch08-conclusion.md) | No new items; reinforces earlier ones |

## Books 2–5

Reports are one file per chapter inside each book folder (file names `chNN-*.md`; list the folder). Highlights:

| Book | Most useful chapters for the platform |
|---|---|
| 2 Chan, Algorithmic Trading | ch. 1 (backtesting), ch. 2 (mean reversion, half-life), ch. 8 (risk) |
| 3 Aronson | ch. 6 (data-mining bias), ch. 5 (hypothesis tests), ch. 8–9 (case study) |
| 4 Kaufman | ch. 21 (system testing), ch. 23 (risk control), ch. 20 (volatility), ch. 22 (practical) |
| 5 López de Prado | ch. 11 (PBO), ch. 14 (PSR/DSR), ch. 3 (triple barrier/meta-labeling), ch. 7 (purging/embargo), ch. 15 (strategy risk) |

## Consolidated backlog

The recurring proposals across all five books, de-duplicated and prioritised, are in [99-consolidated-backlog.md](99-consolidated-backlog.md). **Nothing in it is approved or implemented.**
