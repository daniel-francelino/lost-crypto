---
name: chan2-mean-reversion-tests
description: How to test whether a price series or spread is mean-reverting, from Ernest Chan's "Algorithmic Trading" ch. 2 — ADF test, Hurst exponent and variance-ratio test, Ornstein-Uhlenbeck half-life, linear (z-score) mean-reversion strategy, cointegration with CADF and Johansen, and the risks of the style. Use before building any mean-reversion or spread/basis bot, when estimating a lookback window or holding period, or when checking if a pair/basket relationship is stable.
---

# Testing for mean reversion (Chan, *Algorithmic Trading*, ch. 2)

Page numbers are book pages. **[Adaptation]** = ours for Binance USDT-M perpetuals, not from the book (its examples are FX pairs and ETFs, long and short). Chapter analysis vs. our code: `docs/books/02-algorithmic-trading-chan/ch02-basics-of-mean-reversion.md`. Book-1 version of the half-life: `chan-mean-reversion-momentum`.

## 1. Concepts (pp. 39-41)
Most price series behave like a geometric random walk; **returns**, not prices, oscillate around zero. Mean reversion of prices equals **negative autocorrelation of returns**. Few series are stationary by nature; others can be **constructed** by combining non-stationary series (cointegration). Time-series reversion (to own mean) differs from cross-sectional (relative returns). "Stationary" does not mean confined to a band.

## 2. Three equivalent tests
| Test | What it checks | Reading (pp.) |
|---|---|---|
| **ADF** (pp. 42-44) | Regress `dy(t)` on `y(t-1)` (plus lagged differences); statistic `lambda / SE(lambda)` must be negative and below Dickey-Fuller critical values (depend on sample size and constant/trend; assume zero trend in practice) | USD.CAD: -1.84 vs 90% critical -2.594 => not stationary |
| **Hurst exponent / variance ratio** (pp. 44-46) | `Var(tau) ~ tau^(2H)`: H < 0.5 reverts, H = 0.5 random walk, H > 0.5 trends; the variance-ratio test tests H = 0.5 | USD.CAD: H = 0.49, p = 0.367 => cannot reject random walk |
| **Half-life** (pp. 46-48) | O-U: `dy = lambda*y(t-1) + mu + eps`; expected price converges exponentially to `-mu/lambda`; **half-life = -ln(2)/lambda**. If lambda > 0 do not build a reversion strategy; if ~0 you get too few complete trades | USD.CAD ~115 days |

Practical notes: statistical tests are demanding (>= 90%), but profitability needs less certainty. The half-life gives a **natural time scale** (lookback = small multiple of half-life), so you avoid brute-force optimizing the window (p. 47). A series with a ten-year half-life is not tradable (p. 63).

## 3. Linear mean-reversion strategy (pp. 48-50)
Hold units **proportional to the negative z-score** (price minus moving average, divided by moving std), lookback = half-life. No free parameters, uses every bar (more statistical power than few round-trip trades). The author's own caveats on the example: half-life computed in-sample (look-ahead), unlimited capital, costs ignored. Treat as a **diagnostic**, not a deployable bot.

## 4. Cointegration (pp. 50-60)
A stationary linear combination of non-stationary series.
- **CADF (Engle-Granger)**: regress one series on the other to get the hedge ratio, test the residual; result depends on which series is the regressor. EWA/EWC: -3.64 vs 5% critical -3.359.
- **Johansen**: several series, order-independent, returns the number of cointegrating relations and eigenvectors usable as hedge ratios (largest eigenvalue => shortest half-life). EWA-EWC-IGE basket: half-life ~23 days; linear strategy 12.6% / Sharpe 1.4 **without costs** (the author's example, not evidence for us). The Johansen implementation the author knows accepts a maximum of 12 series (p. 102) — an implementation limit, check your library.

## 5. Pros and cons (pp. 60-61)
Many candidates and often a fundamental reason for a pair's link and its break; short horizons give many trades and statistical confidence. But consistency breeds **over-confidence and over-leverage** (LTCM); breaks happen when leverage is at its max; **stops cannot be justified logically** for the reversion thesis (see `chan2-leverage-risk` for the policy).

## 6. [Adaptation] Where to apply it in the bots
- Candidates: perp vs spot/other-expiry basis, correlated majors (e.g. BTC/ETH ratio), funding-rate series itself (its reversion is a known property of perps — verify with ADF/half-life on our data, do not assume).
- Run ADF + Hurst/VR + half-life on a **rolling** window and require the relationship to hold out of sample; pairs cointegrated in one period often stop being so (book ch. 4, p. 89).
- Keep hedge ratios and the half-life estimated **only from the training window** (the book's example violates this on purpose to illustrate).
- Funding and fees accrue with holding time: the half-life sets the expected hold, so net funding over one half-life must still leave an edge.
- Always continue with `chan2-mean-reversion-build` and `chan2-backtest-significance`.
