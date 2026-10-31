# Book 1 · Chapter 1 — The Whats, Whos, and Whys of Quantitative Trading

*Quantitative Trading*, Ernest P. Chan (Wiley, 2009). Pages are **book pages** (PDF page = book page + 22). Baseline: [00-system-baseline](../00-system-baseline.md). Status: analysis only, nothing implemented.

## 1. Chapter summary (pp. 1–8)

Introductory. No formulas. Claims are the author's opinions and anecdotes, not evidence.

| ID | Concept | Problem it addresses | Pages |
|---|---|---|---|
| C1 | Quantitative trading = trades decided strictly by algorithms tested on history; fundamentals and news count if they become numbers; subjective chart patterns do not. | Separating codifiable strategies from opinion. | 1–2 |
| C2 | Simple strategies; advanced maths did not help the author (own account of losses at institutions). | Complexity as a source of losses. | 2–3 |
| C3 | Keep savings; do not need immediate profit; returns have their own pace. | Pressure for quick results. | 4 |
| C4 | Scale by changing leverage; warns against over-leveraging. | Uncontrolled scaling. | 5 |
| C5 | Manual interference often makes results worse; author admits the urge to exit on P&L swings. | Human override. | 5–6 |
| C6 | Automate step by step: download data, start and stop programs, **alert a phone/support when something goes wrong**. | Operating without watching the screen. | 6–7 |
| C7 | Research must continue because competition erodes profits. | Edge decay. | 6–7 |
| C8 | Start small, grow with know-how. | Ruin risk early on. | 4–5 |

The book does not discuss crypto, 24/7 markets or exchange fees. Anything about crypto below is **our adaptation**.

## 2. Diagnosis

| Concept | Status | Evidence |
|---|---|---|
| C1 | ✅ | Strategies are registered classes; signals are explicit intents. |
| C2 | ⚠️ | Small catalogue; no measure comparing simple vs complex strategies. |
| C3/C8 | ✅ | Paper → testnet → live, live caps, minimum paper days, typed-name approval. |
| C4 | n/a | Spot only; no leverage. Exposure caps exist, a leverage policy does not. |
| C5 | ⚠️ | `pause`/`stop`/`reset` are audited, but no reason is recorded and no intervention metric exists. |
| C6 data | ⚠️ | The trader fetches recent candles itself; historical import is manual only. |
| C6 **alerts** | ❌ | No notification channel (searched `alert`, `notif`, `webhook`, `telegram`, `email`, `smtp` in `api/src`: nothing). Worker heartbeat exists but is only read by the UI. |
| C7 | ✅ | Backtest, sweep, comparison exist. |

## 3. Opportunities

### O1 — Failure alerts *(book: C6, p. 7 · channel and triggers are our adaptation)*
* **Problem:** worker down, stale bot heartbeat, kill switch toggled, reconcile mismatch, live order rejected and daily cap hit go unnoticed without a person looking.
* **Proposal:** a `Notifier` port with one implementation per channel (webhook first, then chat), one file per integration. An evaluator in the worker emits alert events with de-duplication, cooldown and a recovery message. Critical ones also go to the audit log.
* **Benefit:** failures noticed in minutes, unattended.
* **Complexity:** medium (periodic task in the worker, channel secret).
* **Risks:** the alert path dies with the worker (needs an external liveness check, e.g. container healthcheck); a new secret to protect; alert fatigue.
* **Validation:** unit tests for thresholds and de-duplication; integration test that stops the worker and expects one alert through a fake notifier; secrets absent from logs/API.

### O2 — Automatic incremental data import *(book: C6, pp. 6–7 · adaptation)*
* **Problem:** gaps in stored candles are repaired only by manual jobs.
* **Proposal:** a periodic worker task that extends coverage of active pairs to now, reusing the import job; back off on exchange maintenance gaps.
* **Benefit:** backtests always run on current data.
* **Complexity:** low. **Risks:** rate limits; legitimate gaps retried forever.
* **Validation:** integration test with a fake source that leaves a hole and expects it filled.

### O3 — Reason for manual interventions *(book: C5, pp. 5–6 · adaptation)*
* **Problem:** cannot tell whether a stop/pause/reset was a reaction to P&L swings.
* **Proposal:** optional reason on those commands, stored in the audit payload, plus an "interventions per bot" figure.
* **Benefit:** data about our own behaviour. **Complexity:** low. **Risk:** an ignored field.
* **Validation:** test that the reason reaches the audit event.

### O4 — Leverage/exposure policy *(book: C4, p. 5 · deferred)*
No leverage exists. Becomes high priority only if futures/margin are added; revisit with Chapter 6.

### O5 — Simple vs complex comparison *(book: C2, p. 3 · not actionable)*
Rests on one opinion sentence. Later chapters give concrete criteria; do not act on this one.

## 4. Priority

| # | Item | Reliability | Risk mgmt | Backtest quality | Complexity | Depends on |
|---|---|---|---|---|---|---|
| 1 | O1 alerts | high | high | – | medium | worker scheduler, channel secret |
| 2 | O2 incremental import | medium | – | medium | low | existing import job |
| 3 | O3 intervention reason | low | medium | – | low | existing audit |
| – | O4, O5 | deferred | | | | |

## 5. Affected files
* O1: new `notifications` module (port + one file per channel), `worker.py`, `container.py`, `core/config.py`, audit, app status/settings pages.
* O2: `modules/market_data/application/service.py`, `worker.py`, `container.py`.
* O3: `modules/bots/application/service.py`, bots router, audit payload, app control forms.

## 6. Incremental plan
1. O1a: `Notifier` port, fake notifier, condition evaluator (no real channel).
2. O1b: webhook implementation, env configuration, wire into the worker.
3. O1c: status page shows recent alerts and configured channels.
4. O2: periodic incremental import.
5. O3: reason field.

## 7. Acceptance criteria and tests
* One alert per episode within N seconds of a threshold breach, plus one recovery message.
* A failing channel never breaks the worker; the failure is logged.
* No channel secret in logs, audit or API responses.
* Order flow and live safeguards unchanged; unit, integration, ruff and mypy stay green.

## Caveat
The author's profit anecdotes (pp. 3, 8) are personal accounts and must not be used as return expectations.
