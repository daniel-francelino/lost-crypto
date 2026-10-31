# Book 1 · Chapter 4 — Setting Up Your Business

*Quantitative Trading*, Chan (2009). Book pages (PDF = book + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only.

## 1. Chapter summary (pp. 69–78)

A non-technical chapter about the US equity setting (SEC Regulation T, NASD Series 7, SIPC). Most of it does not transfer to a personal crypto system.

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Retail brokerage (free, low leverage, insured) vs proprietary firm (high leverage, rules imposed, not insured). Imposed rules can act as external risk management; unrestricted freedom is a risk when the "big drawdown" comes. | Choosing who holds the capital and who limits you. | 69–71 |
| C2 | Choose a broker on more than commission: execution speed, access to liquidity, product range, and above all an **API** for data and orders plus a **paper-trading account**. Possible to use several accounts to compare real execution quality. | Hidden execution costs; inability to test safely. | 71–74 |
| C3 | Counterparty risk: check the firm's financial strength, registration, and reputation for returning capital. | Losing capital because of the custodian. | 74 |
| C4 | Physical infrastructure can start light (PC, broadband, UPS). Later, **business continuity**: run the programs on a hosted/collocated server to avoid Internet/power outages; monitor remotely. Latency adds slippage in fast markets. | Downtime and latency. | 75–77 |
| C5 | More real-time information is not automatically better (horse-racing study cited). | Information overload. | 75–76 |

No crypto content. Everything about exchanges below is **our adaptation**.

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| C1 external limits | ✅ | Live trading is guarded by operator-set caps (`LiveLimits`), kill switch, approvals, `live_min_paper_days`; they live in the environment, not in the API, matching the idea of limits the operator cannot casually remove. |
| C2 API + paper account | ✅ | Binance spot and testnet behind one `ExchangeRegistry`; paper execution venue exists (`execution/venues/paper.py`). |
| C2 compare execution across venues | ❌ | One exchange only; no record of expected vs actual fill price, so execution quality cannot be compared (see chapter 5). |
| C3 custody/counterparty | ⚠️ | Exchange keys are used with the exchange holding the funds. The system does not state a withdrawal-disabled key requirement or hold an exchange-risk note. To verify rather than assume, check the key-permission handling in `exchanges` before acting. |
| C4 continuity | ⚠️ | Docker Compose with API + worker + Postgres; reconciliation recovers pending orders after a crash. No documented hosting/redundancy plan, no restore test, no external liveness check. |

## 3. Opportunities

### O1 — Document the operating environment and continuity plan *(book: C4, pp. 75–77 · adaptation)*
* Write a short runbook: where the stack runs (not on a laptop that sleeps), restart policy, Postgres backups and a **tested restore**, clock sync, and what happens to open positions if the host is down. Complexity: low (documentation) plus a backup job. Validation: an actual restore into a scratch database.

### O2 — Key-permission policy *(book: C3 spirit, p. 74 · adaptation, not in the book)*
* Require (and verify when the connection is created) that exchange keys are **trade-only, no withdrawal**, and IP-restricted where the exchange supports it. Needs a check of what the Binance adapter can detect from the account-permissions endpoint. Complexity: low–medium. Risk: some exchanges do not expose permissions. Validation: connection verification test with a fake adapter returning a withdrawal-enabled key.

### O3 — External liveness check *(book: C4 monitoring remotely, p. 77 · links to Chapter 1 O1)*
* A check from outside the stack (container healthcheck or an external pinger) so the loss of the whole host is noticed; pairs with the alerting proposed in Chapter 1.

### Not applicable
Retail vs proprietary choice, Series 7, SIPC, Regulation T, dark pools, collocation near an exchange, hiring a newsfeed.

## 4. Priority

| # | Item | Reliability | Risk mgmt | Complexity | Depends on |
|---|---|---|---|---|---|
| 1 | O2 key-permission policy | medium | **high** | low–med | exchange adapter capabilities |
| 2 | O1 continuity runbook + backup restore | high | medium | low | – |
| 3 | O3 external liveness | medium | – | low | Chapter 1 O1 |

## 5. Affected files
`exchanges/application` (connection verification), `exchanges/infrastructure/binance.py`, `docs/` (runbook), `docker-compose.yml` (healthchecks, restart policy), backup script.

## 6. Plan
1. Runbook and backup/restore test (no code risk).
2. Permission check in connection verification, shown in the UI as a clear state.
3. External liveness once alerting exists.

## 7. Acceptance criteria
* A restore from a backup into a clean database is demonstrated and documented.
* A connection with withdrawal permission is refused or loudly flagged in verification.
* No real-money action is required to test any of this.

## Caveat
Chan's cost and hardware figures (2008) are outdated and equity-specific; do not use them as estimates.
