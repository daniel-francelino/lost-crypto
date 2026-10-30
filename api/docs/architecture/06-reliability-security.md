# 06 — Trading Reliability and Security

No strategy is assumed profitable. The goal is that failures (network, process, bugs, bad data) **lose at most a bounded amount and never silently**.

## Preventing duplicate orders (core mechanism)

The dangerous window is: *request sent → response lost → process retries or restarts*.

**Write-ahead intent + deterministic client order id:**

1. Engine computes a deterministic `client_order_id` from `(bot_id, session_id, signal_id, leg)` (hash, truncated to the exchange's length limit; Binance `newClientOrderId`).
2. In **one DB transaction**: insert `orders` row (`status=INTENT`, `UNIQUE(connection_id, client_order_id)`), reserve capital, mark the signal as consumed. Commit.
3. Set `SUBMITTING`, commit, **then** call the exchange with that `client_order_id`.
4. On success → `OPEN`/`FILLED` from the response. On a definite rejection → `REJECTED`, release capital.
5. On timeout/connection reset/5xx (**outcome unknown**) → `UNKNOWN`. Never re-send blindly. Query `fetch_order(client_order_id)`:
   - found → adopt its state;
   - not found after the exchange's consistency window and a confirmation read of open orders + recent trades → safe to resubmit **with the same id** (the exchange rejects duplicates of an id still open, so even a wrong "not found" can't create a second order for the same intent).
6. After restart, the recovery routine processes every order in `SUBMITTING`/`UNKNOWN` the same way before any strategy tick runs.

Additional guards: unique `(session_id, signal_id)` on order intents (re-processing the same bar yields the same intent key → conflict → no-op); per-bot single-writer lock (one active session per bot via partial unique index + advisory lock) so two workers cannot trade the same bot.

## Reliability catalogue

| Topic | Strategy |
|---|---|
| **Per-bot risk limits** | `RiskProfile`: max allocation, max position, max open orders, max order notional, max daily loss, max drawdown → auto-pause + audit |
| **Global limits** | `GlobalRiskPolicy`: total exposure, per-asset exposure, global daily loss; live hard caps from environment (doc 05) |
| **Capital reservation** | Reserving funds is part of the order-intent transaction (`balances.locked`); released on reject/cancel/fill reconciliation. Prevents two bots from spending the same funds |
| **Position sizing** | Pluggable `PositionSizer` in risk; final quantity rounded **down** to lot size; rejected if below min quantity/notional |
| **Stop-loss** | Signal carries protective level; risk requires it per policy. MVP: engine-monitored stop (candle/tick check) executing a market/limit exit via normal pipeline. Later: exchange-native stop orders (survive a worker outage). Document the gap: engine-side stops do **not** protect while the worker is down → hence heartbeat alerts and kill-switch |
| **Idempotency** | Client order ids, unique constraints, idempotent candle upserts, idempotent tick processing keyed by `(bot, bar_close)`; HTTP `Idempotency-Key` on mutating endpoints that create resources |
| **Rate limits** | Per-connection token bucket in the exchange adapter (weight-aware); backoff on 429/418; engine degrades (skips non-essential calls) rather than bursts |
| **Network failures** | Timeouts on every call; classification into transient / permanent / unknown-outcome; circuit breaker per connection trips bot to `paused` after N consecutive failures |
| **Retry policy** | Reads: exponential backoff with jitter, bounded attempts. Writes (create/cancel): retried only if failure provably happened before reaching the exchange; otherwise reconcile first. Cancel is naturally idempotent |
| **Reconciliation** | `Reconciler` runs on startup, after any `UNKNOWN`, and periodically (e.g. every minute): compares local open orders/fills/balances with the exchange; auto-heals state we can prove (missing fill, status drift); **raises alert and pauses the bot** for anything unexplained (unknown external order, balance drift beyond tolerance) |
| **Partial fills** | `PARTIALLY_FILLED` state; `filled_qty` = Σ fills; remaining qty stays reserved; strategy sees the position change on the next tick; cancel of partially filled order keeps fills |
| **Fees** | Each fill stores fee amount + currency (including BNB-discount case); portfolio ledger books fees as separate entries; analytics is net of fees; simulators use configurable maker/taker fee models |
| **Slippage** | Simulated venues apply a `SlippageModel` (fixed bps / volume-based); live slippage measured as `fill_price − expected_price` and stored for analytics |
| **Precision & minimums** | `OrderNormalizer` uses exchange market info (tickSize, stepSize, minQty, minNotional) with `Decimal` and exchange rounding rules, applied in every mode; reject locally with a clear reason before hitting the exchange |
| **Emergency shutdown** | Global kill switch: (1) stops new intents, (2) cancels open orders (configurable), (3) optionally flattens positions (explicit), (4) sets bots `paused`/`error`. Triggerable by API (`POST /system/kill-switch`), CLI, automatic risk triggers, or a file/DB flag the worker polls even if the API is down |
| **Audit logging** | Append-only `audit_events` for: bot state changes, config versions, risk decisions, order lifecycle, mode changes, credential access, kill-switch, logins. Includes actor, correlation id, before/after summary. No UPDATE/DELETE grants for the app role on this table |
| **Data staleness** | Strategies receive freshness metadata; engine refuses to trade if last candle/ticker is older than a threshold |
| **Clock drift** | Binance `recvWindow` and time sync check at startup; alert on drift |
| **Time/ordering** | All timestamps UTC; exchange timestamps stored alongside local receive time |

## Secure credential storage

- API keys/secrets are **never** stored in plaintext, logs, API responses, or the bots table. `exchange_connections` stores only an encrypted blob + key id + non-secret metadata (label, environment, key fingerprint/last 4 chars).
- Encryption: AES-GCM/Fernet with a master key from environment/secret manager (`CREDENTIAL_MASTER_KEY`), key id for rotation. Docker secrets or an external vault later; never committed to git.
- Decryption occurs only inside the `CredentialVault` adapter used by the exchange factory in the **worker**; the API process may not need decrypt rights at all (it only writes encrypted values, via the vault's `store`).
- Secrets wrapped in `SecretStr`; log filters redact common patterns; no secrets in exception messages.
- Principle of least privilege on the exchange side: trade-only, no withdrawals, IP whitelist, separate keys per environment.
- API: credential endpoints are write-only (`PUT`), reads return masked metadata.
- API authentication for the HTTP interface (single-user MVP: strong token/JWT, HTTPS terminated by a proxy); CORS restricted to the frontend origin; rate limit on auth.

## Failure scenarios

| Scenario | Outcome |
|---|---|
| Network drops after `create_order` sent | Order is `UNKNOWN`; reconciliation by client id; no duplicate |
| Worker killed between intent commit and send | Recovery sees `INTENT`/`SUBMITTING`; looks up by client id; sends if absent |
| Worker killed after send, before commit of response | Same; exchange has the order → adopted |
| Two workers start accidentally | Advisory lock / partial unique session index → second one refuses |
| Exchange outage | Circuit breaker → bot paused, alert; no order storm on recovery |
| Candle feed gap | Gap detected; back-fill for state, no trading on stale data |
| DB unavailable | Worker stops placing orders (no write-ahead possible = no trade); retries connect |
| Wrong mode/credentials | Environment tag mismatch → connection refused at construction |
| Bug in strategy returns huge size | Risk caps (order notional, exposure) reject/resize |
