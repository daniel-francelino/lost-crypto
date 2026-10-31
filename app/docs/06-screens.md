# 06 — Screens

Each screen: route, API calls, lost-ui pieces, states, permissions. The product behaviour (what a bot, a backtest, the kill switch *mean*) is documented in the backend's [architecture docs](../../api/docs/architecture/README.md); this is only the UI contract. UI labels are Brazilian Portuguese, in quotes.

All authenticated screens sit under `_app` (shell with `BackofficeLayout`). Every screen implements, in this order: **skeleton → error with retry → empty → no results → data** (aura UI-2), and the polling of [04](04-api-client.md#polling-decision-f10).

## Global shell

| Element | Behaviour |
|---|---|
| Sidebar sections | "Visão geral" (Dashboard) · "Operação" (Bots, Conexões) · "Pesquisa" (Backtests, Dados de mercado) · "Sistema" (Status, Auditoria) · "Configurações" (Perfil, Usuários — admin) |
| **Safety strip** in the top bar, always visible | Kill-switch state (`GET /system/status`), worker alive/stale, `observed` bots count, environment (`local`/`prod`), and `API offline` when polling fails. Clicking opens the system screen |
| Kill switch button (admin) | In the top bar, one click → confirmation (`AlertDialog`) → `PUT /system/kill-switch {active:true, reason}`. **Releasing** it asks for a reason too and is not a single click. See [07](07-ux-rules.md#kill-switch) |
| User menu | name, role badge, "Meu perfil", "Sair" |
| Breadcrumbs | from the route; bot name resolved from the cached detail |

## 1. Login — `/login`

`LoginPage`; see [05](05-authentication.md#login-screen). Public. If a session already exists, redirect to `redirect` or `/`.

## 2. Dashboard — `/`

Calls: `GET /bots/overview` (10 s), `GET /system/status` (5 s).

* Top: stat tiles — total equity of running bots, today's realized PnL, bots running / paused / error, open positions. (No endpoint sums across bots: either **ask the backend for a portfolio summary** or show per-bot only. Do not add money in the browser — F5. **Open request R1**.)
* A card per bot from `BotOverviewOut`: name, symbol/timeframe, strategy, **mode badge** (see 07), state (desired→observed), equity, return %, `in_position`, last price, heartbeat age. Click → bot detail.
* "Atenção" panel: bots in `error` (with `last_error`), stale bots (`system.stale_bots`), kill switch active, connections `invalid`.
* Empty state: "Você ainda não tem bots" → admin sees "Criar bot".
* Pieces: `PageHeader`, `Card`, `Badge`, `Empty`, `Skeleton`; stat tile per request L3 in [03](03-lost-ui.md).

## 3. Bots — `/bots`

`GET /bots` (+ overview for equity). `DataTable` with columns: name, symbol, timeframe, strategy, mode, state, equity, return %, heartbeat. Client-side search by name and filter by state/mode. Primary action (admin): "Novo bot".

## 4. New / edit bot — `/bots/new`, edit inside the detail

`POST /bots`, `PATCH /bots/{id}`. Admin only.

* Form (lost-ui `Form`): name, exchange (options come from `exchanges` in `GET /system/status`, the ids the backend has registered; **To verify** that this field means "enabled exchanges" when the screen is built), symbol, timeframe (`Timeframe` list), strategy (`GET /strategies`) + its parameters via `FormBuilder`, initial capital, fee rate, slippage bps, **risk block** (`max_position_fraction`, `max_order_notional`, `max_daily_loss_pct`, `max_drawdown_pct`, `max_consecutive_losses`, `max_risk_per_trade_pct`, `require_stop_loss`, `max_candle_range_pct`), and execution **mode**.
* **Mode choices are `paper` and `testnet` only.** The backend refuses to create or PATCH a bot into `live`; live has its own flow (screen 6). The mode option for live is not offered here, with an inline explanation that points to "Promover para live".
* Testnet needs a `connection_id` of an active testnet connection (select from `GET /exchange-connections`); paper must have none.
* Editing a running bot is refused or voids a live approval (any config change bumps `config_version`): the form says so before saving, and the detail page shows the resulting state.
* Validation: `rules` for required/ranges, zod for the money regex; server 422 array → field errors. Unsaved-changes warning.

## 5. Bot detail — `/bots/$botId`

The most important screen. Tabs (URL search param `tab`): **Resumo · Ordens · Sinais · Desempenho · Configuração · Auditoria**.

| Tab | Calls | Content |
|---|---|---|
| Header | `GET /bots/{id}` | name, **mode badge**, desired vs observed state, `last_error`, heartbeat age, controls |
| Resumo | `/portfolio`, `/equity` | cash, quantity, avg entry, last price, equity, unrealized/realized PnL, fees, stop/take-profit, reserved cash, `native_stop_active`; equity `AreaChart` |
| Ordens | `/orders?limit` | `DataTable`: time, side, quantity, status (`OrderStatus` badge incl. `UNKNOWN`), filled qty, avg price, reject reason, `client_order_id` (copyable) |
| Sinais | `/signals?limit` | time (bar, UTC), side, kind, reason, **decision** and `decision_reason` (why the risk layer accepted/rejected it) |
| Desempenho | `/performance` | `MetricsOut` as tiles + table (win rate, profit factor, drawdown, buy-and-hold comparison) |
| Configuração | `GET /bots/{id}` | read-only config, strategy params, risk limits; "Editar" for admin |
| Auditoria | `/audit-events?bot_id=` | `Timeline` of events for the bot |

**Controls** (admin): "Iniciar", "Pausar", "Parar", "Resetar portfólio" (stopped bots only, as the backend requires; destructive confirmation naming the bot). Buttons enable by state (e.g. no "Iniciar" while desired=running). Starting a **live** bot needs the approval flow (screen 6). Commands answer 202 and the header shows "iniciando…" until `observed_state` follows ([04](04-api-client.md#asynchronous-commands-desired-vs-observed-state)).

## 6. Live promotion and approval — inside bot detail

Only for admins; only when the backend can accept live (the readiness endpoint tells). A guided flow with `Stepper` in a `Modal`/`Slideover`, **never** a single button:

1. **Readiness** — `GET /bots/{id}/live-readiness` → list of `CheckOut {name, ok, detail}` + `ready`. Failed checks are shown with their `detail`; nothing can proceed while `ready` is false. Refetches on demand.
2. **Promote** — pick an `active` live connection (`GET /exchange-connections`, filter `environment=live` & `status=active`), `POST /bots/{id}/promote-to-live {connection_id}`. Preconditions the UI mirrors (the backend enforces them): bot stopped, flat position, clean paper history.
3. **Approve** — the operator **types the exact bot name**; `POST /bots/{id}/live-approvals {confirm_name}` returns `{confirmation_token, expires_at}`. The token is **single-use and short-lived** (minutes) and bound to the current config version.
4. **Start** — `POST /bots/{id}/start {confirmation_token}`. The token is held in component state only (not the URL, not the cache, not storage), with a visible countdown to `expires_at`; when it expires the flow returns to step 3.

The approval is required on **every** start of a live bot, including after a pause or a kill switch. The "Iniciar" button on a live bot always opens this flow at step 3 (or 1 if not ready); there is no way to start a live bot from the list or the dashboard.

Backend refusals (422 strings: worker switch off, `APP_ENV` not prod, caps missing, connection not active, no approval, version mismatch) are shown **verbatim** in the dialog; they are the explanation.

## 7. Backtests — `/backtests`, `/backtests/new`, `/backtests/$runId`, `/backtests/compare`, `/backtests/sweeps/$sweepId`

* **List** `GET /backtests?limit=50`: status (`JobStatus`), strategy, symbol, timeframe, period, return %, drawdown. Select 2–4 → "Comparar" → `GET /backtests/compare?ids=…` as lines on one `LineChart` + metrics table.
* **New** `POST /backtests` (202): exchange, symbol, timeframe, period (UTC date range), strategy + params (`FormBuilder`), initial capital, fee rate, slippage, seed, test fraction (out-of-sample split). Before submitting, show data **coverage** for that range (`GET /market-data/coverage`) and block/warn when there are gaps or no candles, with a shortcut to import them.
* **Sweep** `POST /backtests/sweeps`: the same form with a **grid** (list of values per parameter). Result page `/backtests/sweeps/$sweepId`: ranked runs, `skipped` combinations and the backend's `note` about ranking (the page shows that note **prominently**: sweeps overfit; train vs test metrics side by side).
* **Run detail** `GET /backtests/{id}` polled every 2 s until `completed|failed`: metrics, **train vs test segments** (`SegmentsOut`) side by side, equity `AreaChart` (`/equity`), trades table (`/trades`), `data_hash` and `seed` for reproducibility, `error` when failed. A "Criar bot com estes parâmetros" action (admin) opens the new-bot form pre-filled (route state, not a module import).
* The page always labels results "histórico simulado — não garante resultado futuro" near the headline numbers; out-of-sample numbers are shown with equal weight to in-sample.

## 8. Market data — `/market-data`

* Coverage (`GET /market-data/coverage`) by symbol/timeframe/exchange: first, last, count, **gaps** list.
* Candles preview (`GET /market-data/candles`, bounded by `limit`): table now, price chart when request L1 lands.
* Imports: `POST /market-data/imports` (202) with symbol/timeframe/range; list `GET /market-data/imports` with `JobStatus`, `candles_imported`, `error`; polling per row until finished. Admin only for the form.

## 9. Exchange connections — `/exchanges`, `/exchanges/new`

`GET /exchange-connections`, `POST`, `POST /{id}/disable`. Table: label, exchange, **environment badge** (testnet / live), `api_key_hint`, status, verified at. Creating: see [05](05-authentication.md#exchange-keys). `pending` live connections show "aguardando verificação do worker"; the page polls every 10 s while any is pending. Disable = destructive confirmation (a bot using it cannot run).

## 10. System — `/system`

`GET /system/status`, `GET/PUT /system/kill-switch`. Worker (alive, last heartbeat, age), bots by state, stale bots, the registered exchange ids, and the kill switch with its reason and `changed_at`. This is also the page the safety strip links to. The kill switch control is described in [07](07-ux-rules.md#kill-switch).

## 11. Audit — `/audit`

`GET /audit-events?bot_id&limit`: `DataTable` of time, actor, event type, entity, bot, expandable `payload` (rendered as formatted text). Filters on the client over the loaded window, with a visible "mostrando os últimos N" (see [04](04-api-client.md#lists)). Read-only for everyone.

## 12. Settings — `/settings/profile`, `/settings/users`

* Profile: `ProfilePage` (username, role, `onChangePassword`; note it signs out every device).
* Users (admin): `GET/POST /auth/users`, `disable`/`enable` (an admin cannot disable themselves; the button is disabled with the reason). New-user form validates the password policy client-side to match the backend (≥ 12 characters, not the username); the backend result is the authority.

## Open requests to the backend (found while specifying the screens)

| ID | Need | Why |
|---|---|---|
| R1 | A portfolio summary (total equity, today's PnL, exposure across bots) | The browser must not add money (F5) |
| R2 | Pagination/filters on audit, orders and backtests lists | Lists are bounded by `limit` only (04) |
| R3 | A way to tell the UI whether live is possible at all (`LIVE_TRADING_ENABLED`, caps set) without trying and failing | To hide or explain the live flow up front; today only `live-readiness` per bot hints at it |
| R4 | Role/capabilities in `/auth/me` (not only `role`) | Lets the UI follow backend permission changes without a deploy |

These are backend changes: record them in the API docs when accepted; the frontend does not work around them silently.
