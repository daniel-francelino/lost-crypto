# Book 5 · Chapter 15 — Understanding Strategy Risk

*Advances in Financial Machine Learning*, López de Prado (2018). Book pages (PDF = book + 27). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

**Reading depth:** pp. 211–217 were read (symmetric and asymmetric payouts, implied precision and frequency, probability of strategy failure and the start of the bootstrap algorithm). The rest of the algorithm, the numerical examples and the exercises (pp. 218–220) were **not** read.

**Relevance:** a compact, closed-form way to relate **win rate (precision), payoff sizes (profit-taking/stop-loss) and bet frequency** to the Sharpe ratio, and to ask how fragile a strategy is to small changes in its hit rate. It maps directly onto trend/breakout statistics the platform already reports (win rate, average win/loss, number of trades).

## 1. Chapter summary (pages read)

| ID | Concept | Pages |
|---|---|---|
| C1 | Most strategies have explicit or implicit **exit conditions** (profit-taking, stop-loss; even without a stop there is an implicit limit — margin call or pain). Modelling outcomes as a **binomial process** reveals which combinations of betting frequency, odds and payouts are uneconomic and when a strategy is vulnerable to small changes in them. | 211 |
| C2 | **Symmetric payouts** (profit `π` with probability `p`, loss `−π` with `1−p`; `n` IID bets per year): `E[X] = π(2p−1)`, `V[X] = 4π²p(1−p)`, annualised Sharpe `θ[p, n] = (2p−1)/(2·sqrt(p(1−p)))·√n` — "a rescaled t-value of `p` under `H₀: p = 1/2`"; `π` cancels. Even a small edge gives a high Sharpe with a large `n` (the economic basis of high-frequency trading): for `p = 0.55` an annualised Sharpe of 2 requires **396 bets/year**; weekly bets (`n = 52`) need `p ≈ 0.6336` for Sharpe 2. Sharpe depends on **precision**, not accuracy (passing is neither rewarded nor punished). Solution for the implied precision: `p = (1/2)(1 + sqrt(1 − n/(θ² + n)))`. | 211–213 |
| C3 | **Asymmetric payouts** (`π₊ > 0` w.p. `p`, `π₋ < π₊` w.p. `1−p`): `E[X] = (π₊−π₋)p + π₋`, `V[X] = (π₊−π₋)²p(1−p)`, `θ[p, n, π₋, π₊] = ((π₊−π₋)p + π₋)/((π₊−π₋)·sqrt(p(1−p)))·√n`; reduces to the symmetric case when `π₋ = −π₊`. Solving a quadratic gives the **implied precision `p`** for a target Sharpe (Snippet 15.3) and the **implied betting frequency `n`** (Snippet 15.4). Example: `n = 260`, `π₋ = −0.01`, `π₊ = 0.005`, target Sharpe 2 requires `p = 0.72`; a small change in `p` (0.70 → 0.72) moves Sharpe from 1.173 to 2 — **the strategy is vulnerable to small changes in `p`**; the more negative `π₋` (for given `n`), the higher `p` needed; fewer bets (smaller `n`) need higher `p`. | 213–216 |
| C4 | **Probability of strategy failure**: `p_θ*` = the precision below which the strategy underperforms a target Sharpe `θ*`; because `p` is unknown, model it as a random variable; **strategy risk ≠ portfolio risk**: "strategy risk is the risk that the investment strategy will fail to succeed over time" (a question for the CIO), not the volatility of the underlying portfolio (the CRO's number). Example: a drop in `p` from 0.70 to 0.67 wipes out the profits. Failure probability `P[p < p_θ*]`. | 216–217 |
| C5 | **Algorithm (start)**: from the series of bet outcomes `{π_t}`, estimate `π₋ = E[π_t | π_t ≤ 0]`, `π₊ = E[π_t | π_t > 0]` (alternatively fit a two-Gaussian mixture with the EF3M algorithm), the annual frequency `n = T/y`; then **bootstrap the distribution of precision**: draw `n·k` outcomes with replacement (k = years investors use to assess the strategy, e.g. 2), compute precision `p_i` for each of `I` iterations, fit its density `f[p]` (KDE) and compute `P[p < p_θ*]` (the rest of the algorithm — the approximate closed form with `E[p]` — was not read). | 217 |

## 2. Diagnosis (verified in code)

| Concept | Status | Evidence |
|---|---|---|
| Win rate, average win/loss, profit factor, trade count | ✅ | In `Metrics`. |
| Bet outcome series (per-trade returns) | ✅ | Trades are stored; per-trade net P/L is available. |
| Annualised bets per year | ⚠️ | Derivable from trades and period; not reported. |
| Implied precision / Sharpe from `{p, n, π₊, π₋}` | ❌ | — |
| Bootstrap distribution of win rate / strategy failure probability | ❌ | — |
| Distinction between strategy risk and portfolio risk | ❌ | Risk metrics are drawdown-based (portfolio risk); no "will this strategy still work" metric. |

## 3. Opportunities

### O1 — "Required win rate" calculator and fragility indicator for every backtest *(book: C2, C3, pp. 211–216)*
* **Proposal:** from a backtest's trade list compute `π₊` (mean winning trade return), `π₋` (mean losing trade return, negative), observed precision `p̂` (win rate), and bets per year `n`. Report: (a) the analytical annualised Sharpe implied by `{p̂, n, π₊, π₋}` (consistency check vs the empirical Sharpe from the equity curve); (b) the **break-even precision** `p_0` (Sharpe = 0 ⇒ `p_0 = −π₋/(π₊ − π₋)`) and the **precision needed for Sharpe 1 and 2**; (c) the **margin of safety** `p̂ − p_0` and `p̂ − p_{θ=1}`, expressed in standard errors of a binomial proportion, to show how many percentage points of win-rate decay the strategy tolerates before it stops being worth running.
* **Why:** trend strategies in this platform have win rates around 30–40% and payoff ratios > 1 (book 4 ch. 22 C15); this metric makes explicit how thin the margin is and how it depends on trades per year. A strategy that needs `p` within 2 points of its estimate is fragile, particularly with few trades (the standard error of `p̂` with 40 trades is about 7.7 points).
* **Complexity:** low. **Risks:** the model assumes two-point payoffs and IID bets; real trade returns are widely dispersed, so `π₊`/`π₋` means hide the distribution (the Sharpe formula uses only means; use the empirical per-trade standard deviation as a check); trend systems have serially dependent outcomes. **Validation:** the book's numerical examples (p = 0.55 → n ≈ 396 for Sharpe 2; n = 52 → p ≈ 0.6336; n = 260, π₋ = −0.01, π₊ = 0.005, Sharpe 2 → p = 0.72) reproduce to the printed precision; at `p_0` implied Sharpe = 0; invariance to scaling payouts.

### O2 — Strategy-failure probability by bootstrap *(book: C4, C5, pp. 216–217)*
Implement the algorithm start: resample trade outcomes to build the distribution of the precision over a horizon of `k` years (`n·k` draws), compute `P[p < p_θ*]` for target Sharpe thresholds (0 and 1) and display "probability this strategy's Sharpe falls below 0/1 over the next k years". Use a block bootstrap if outcomes are serially dependent (our addition). Combine with PSR/DSR (ch. 14) and PBO (ch. 11) as the "credibility panel": PBO about the *selection*, PSR/DSR about the *statistical significance*, strategy-failure probability about *future fragility*. **Complexity:** low–medium. **Risks:** bootstrap from a small trade set is itself noisy; selection bias is not corrected (use out-of-sample/locked-segment trades whenever possible). **Validation:** seeded determinism; coverage test on synthetic Bernoulli payoffs (nominal vs observed interval).

### O3 — Use required precision × frequency as a design rule when choosing timeframes *(book: C2, C3, pp. 212–216)*
Lower timeframes mean larger `n` and therefore a smaller edge is needed for a given Sharpe — but costs per bet shrink `π₊` and enlarge `π₋` (fees and slippage are part of both; book 4 ch. 16/22). Provide an interactive calculator in the UI where the user enters `{win rate, average win, average loss (after costs), trades/year}` and sees the Sharpe, the break-even precision, and the implied precision for target Sharpe values. **Complexity:** low. **Validation:** as in O1.

### O4 — Report "strategy risk" alongside portfolio risk *(book: C4, p. 217)*
Add the vocabulary to the docs and UI: drawdown and volatility are portfolio risk; the margin of safety in win rate, payoff and frequency is strategy risk. Strategy-risk metrics (O1/O2) are the ones that should trigger a pause or reduction in the lifecycle rules (ch. 1 O1; book 4 ch. 22 O2, ch. 21 O9): e.g. when the live win rate over the last `m` trades falls below `p_0` + margin with statistical significance (sequential binomial test — book 4 ch. 23 O8). **Complexity:** low–medium.

### Not applicable
EF3M mixture fitting (not read), high-frequency practicalities, the IID assumption beyond a sensitivity note.

## 4. Priority

| # | Item | Backtest quality | Risk mgmt | Reliability | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 required win-rate / fragility | high | high | – | low | trade list |
| 2 | O3 interactive calculator | medium | medium | – | low | O1 |
| 3 | O4 vocabulary + live monitor link | – | high | high | low–medium | alerts |
| 4 | O2 failure probability by bootstrap | high | high | – | low–medium | O1 |

## 5. Affected files
`analytics/domain/` (strategy-risk module), `docs/openapi.json`, app backtest results and a small calculator page, tests.

## 6. Incremental plan
1. Closed-form functions with the book's examples as tests.
2. Backtest-level fragility panel.
3. Bootstrap failure probability.
4. Live monitoring hooks (paper/live), after alerts exist.

## 7. Acceptance criteria and tests
* Reproduces the book's printed examples; monotonicity in `p` and `n`; break-even precision gives zero Sharpe; bootstrap deterministic with a seed; ruff, mypy, existing tests green.

## Caveats
The framework treats bets as IID Bernoulli outcomes with two payoff levels: it is a stylised model; trend strategies have fat-tailed winners (book 4 ch. 22) so the two-point approximation can mislead, and serial dependence between consecutive trades is ignored. The Sharpe here is per-bet-based and annualised by √n, not the time-series Sharpe from the equity curve. Pages 218–220 (remaining algorithm, examples, exercises) were not read.
