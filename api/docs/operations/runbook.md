# Runbook — operating Lost Crypto

How to run the stack so that an outage, a lost disk or a changed API key does not cost money. Written from book 1 ch. 4 (Chan, *Setting Up Your Business*), adapted to a self-hosted crypto bot. Read it before turning on testnet or live trading.

## 1. Where it runs

* An **always-on server** (a small VPS is enough), never a laptop that sleeps or loses Wi-Fi. The stack is `docker compose up -d` (Postgres, API, worker).
* `restart: unless-stopped` brings the API and the worker back after a crash or a reboot. The worker's own `healthcheck` (`python -m worker --healthcheck`) marks the container `unhealthy` when its heartbeat in the database is older than `WORKER_STALE_AFTER_SECONDS` (60 s).
* Give the server a **fixed public IP** and restrict the live API key to it on the exchange.

## 2. What protects an open position when the server is down

* Only a **stop resting on the exchange** survives an outage. Live bots must have `risk.require_stop_loss=true` (enforced by the live readiness check) and the strategy places the stop on Binance right after the entry.
* If placing that stop failed, the position is exposed. The **Status** screen lists "Posições sem stop na exchange" and the bot shows "Sem stop na exchange"; `GET /api/v1/system/status` has `unprotected_positions`. Fix it (place the stop by hand on the exchange, or close the position) before leaving the system alone.
* The kill switch (`PUT /api/v1/system/kill-switch`, or the button in the top bar) stops new entries everywhere; exits keep working.

## 3. Knowing that it is down

The app only warns whoever has it open. To be told when the whole host is gone, point an **external** monitor (UptimeRobot, Healthchecks.io, a cron job on another machine) at:

```
GET https://<your-host>/api/v1/health/worker
```

It answers **200** while the worker's heartbeat is fresh and **503** when it is stale. No login is needed and it reveals nothing sensitive. The Status screen shows this URL with a copy button.

## 4. Backups

```bash
make backup          # local:  pg_dump into BACKUP_DIR (default ./backups), recorded in the DB
make restore-check   # restores the latest dump into a throwaway DB and checks the row counts
docker compose exec api python -m manage backup          # in Docker (dumps go to the backups volume)
docker compose exec api python -m manage restore-check
```

* A backup only counts once a **restore check** of it succeeded. The Status screen shows "Backup: em dia / atrasado" (no successful backup in 26 h, or the last restore check failed).
* Schedule both daily (cron on the host, e.g. `15 3 * * *` backup and `45 3 * * *` restore-check) and keep `BACKUP_KEEP` (14) dumps.
* **Copy the dumps off the server** (another machine or object storage). A backup on the same disk does not survive the disk.
* The dump contains the exchange credentials **encrypted** with `CREDENTIAL_MASTER_KEYS`. Keep the master key in a password manager, **separately** from the dumps: without it the connections cannot be opened (recreate them with new keys); with both together, a leak exposes the keys.

### Restoring for real

1. Stop the worker (`docker compose stop worker`) so nothing trades while you restore.
2. Create an empty database and `pg_restore --no-owner --dbname=<url> <dump>`.
3. `alembic upgrade head`, then start the API and the worker with the same `CREDENTIAL_MASTER_KEYS`.
4. The worker reconciles every exchange bot with the account on its first pass; check the Status screen and the reconciliation results before resuming bots.

## 5. Clock

The trader decides that a candle has closed by the server clock, and Binance refuses signed requests outside its time window. Run NTP (`timedatectl set-ntp true` on most Linux hosts). The worker measures the difference with the exchange every minute: above **1 s** the Status screen warns; above **5 s** it opens **no new live positions** (exits continue) until the clock is fixed.

## 6. API keys

* Live keys: **Spot trading only**, no withdrawals, no universal transfers, restricted to the server's IP. The worker refuses anything else when the key is created and **checks again every day**; the Connections screen has "Verificar agora".
* If a key later becomes too permissive (someone enables withdrawals), the connection gets a warning: **new entries are refused, exits continue**, and live approval fails until the key is fixed and checked again.
* Rotating a key: create a new connection with the new key, point the bots at it, disable the old connection, then delete the old key on the exchange.
* Rotating the master key: add the new key in front of `CREDENTIAL_MASTER_KEYS` (comma separated; the first one seals new secrets, the others still open old ones), restart, re-create the connections, then drop the old key.

## 7. Counterparty risk

The exchange holds the money. Keep on it only the capital the bots use; move the rest out.

## 8. Operator judgment decisions (book 2 ch. 8, C9)

The system enforces limits; some decisions stay with the operator. Write them down before you need them, and record the outcome as a note on the bot or backtest (`POST /bots/{id}/notes`), so that the reason survives the memory of it.

1. **Reducing size before a known event.** Chan's advice is *not* to do it if the model already survived a similar stress, and to start conservative before it has been tested. Before an event, look at the backtest's worst period (`/backtests/{id}/sizing`, `/exposure-curve`) and at the bot's `max_drawdown_pct`: if the event is within what the model already lived through, leave it; if it is not, lower `max_position_fraction` (an edit that voids a live approval) rather than trading by feel.
2. **Size by strategy, not as a joint portfolio.** Each bot is its own sub-account with its own limits; there is no covariance model and no pooled Kelly. A strong bot does not subsidise a weak one, which is why a weak one is easy to see and to retire.
3. **When to end a model.** Use the signals the system gives, in this order: the `performance_degraded` alert (realized Sharpe below half of the backtest's, or a drawdown deeper than the backtest's maximum, after 30+ live returns), the divergence checklist of the bot, and its interventions count. A bot whose drawdown limit should end it, rather than wait for you, can use `drawdown_action = stop`; to start it again, reset its portfolio **with a reason** (that also starts a new drawdown peak). Keep `pause` for bots you are willing to resume by hand. Use `stop` in paper first; nothing here weakens a live safeguard.
4. **A divergence from the backtest is often a regime change, not a backtest bug.** Check the named regime breaks and the per-stretch metrics of the backtest before concluding that it was wrong, and do not add rules to patch the last loss (that is how a backtest becomes overfit).
5. **A stop that filled far worse than planned** (`protective_exit_slippage` alert) is a fact about liquidity, not bad luck: look at the order's realized slippage in the bot's execution tab and decide whether the size or the symbol is the problem. Stops are stop-market on purpose (see `docs/architecture/13-live-trading.md`).

None of these is automated, and none of them is a guarantee: the numbers behind them come from history.
