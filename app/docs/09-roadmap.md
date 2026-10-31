# 09 — Roadmap

Order of work for the frontend, aligned with what the backend offers (backend phases 0–5 are implemented). Safety-relevant screens came **after** the read-only ones, so the operator could watch before being able to act.

| Step | Delivers | Status |
|---|---|---|
| **F0 Scaffold** | Vite + TanStack Start (SPA mode), strict TypeScript, Tailwind 4, `lost-ui`, ESLint with module boundaries and money/date rules, Prettier, husky, Vitest, Playwright, CI | ✅ |
| **F1 API client + session** | `lib/shared/api` (client, `ApiError`, zod at the boundary, single-flight refresh), `QueryKey`, `format.ts`, `dates.ts`, logger | ✅ |
| **F2 Auth** | login with redirect, session bootstrap through the refresh cookie, logout, profile + password change, `can()`, role-aware navigation, forbidden page | ✅ |
| **F3 Read-only operations** | safety strip + status page, dashboard (totals per mode and currency), bots list, bot detail with six tabs, audit, polling with stale marks | ✅ |
| **F4 Controls** | create/edit bot (paper/testnet), strategy parameter form, start/pause/stop/reset with desired-vs-observed handling, kill switch (activate/release) | ✅ |
| **F5 Research** | market data (coverage, preview, imports with polling), backtests (run, train/test, trades, equity), sweeps, comparison | ✅ |
| **F6 Exchanges** | connections list/create/disable with verification states | ✅ (UI only; see below) |
| **F7 Live flow** | readiness → promote → typed-name approval with countdown → start with token; live visual treatment | ✅ (refusal path only; see below) |
| **F8 Admin** | users: create, disable, enable | ✅ |
| **F9 Hardening** | accessibility scans, 360 px checks, dependency audit, headers and runbook ([10](10-deployment.md)) | ✅ for what is listed below |

## What was verified

Run on 2026-10-31 against the Compose stack (API + worker + PostgreSQL, authentication on, a real admin and viewer):

| Check | Result |
|---|---|
| `lint --max-warnings 0`, `tsc --noEmit`, `prettier --check`, `check:consistency` (10 enums vs the backend's `openapi.json`) | pass |
| Unit tests (Vitest): API client (single-flight refresh, 401 retry, 422 → field errors, paging header), session, formatters (decimal strings, signs), dates (UTC), redirect safety, strategy params, bot and backtest forms, chart rows, env, log redaction | 46 pass |
| `npm run build` | pass; `dist/client` ≈ 1.9 MB with `_shell.html` |
| `npm audit --omit=dev --audit-level=high` | 0 vulnerabilities (moved to zod 4 for an advisory in zod 3) |
| End to end (Playwright/Chromium, real backend): anonymous redirect with way back, wrong password, login → reload keeps session → logout, dashboard totals, viewer cannot write (no buttons; forbidden pages), create paper bot → start → "Rodando" → stop with named confirmation → audit tab, live promotion refused with the server's blockers, kill switch blocks start and release needs a reason, every main screen loads | pass |
| axe (WCAG 2 A/AA) on login and eight main screens, light **and** dark | pass; it found and fixed: a link whose `aria-label` did not match its text, and a destructive button failing contrast in dark mode (worked around, [L5](lost-ui-requests.md)) |
| 360 px layout of six screens: no horizontal overflow | pass |
| Screenshots of dashboard, bot detail, orders, new backtest at 1280 px | looked at by hand |

## What was NOT verified

* **Anything with real exchange keys or real money.** Testnet connections and testnet bots were never created through the UI against Binance's testnet; the live flow was only exercised up to the server's refusal (live is disabled in the stack). The approval/start steps (typed name, token countdown, start with token) are implemented, **not** run end to end.
* The sweep result page, backtest detail with train/test segments, the comparison chart and market-data import were not driven with real completed runs by the automated tests; they were only loaded (new-backtest form and list screens) or looked at.
* A real static host, the security headers ([10](10-deployment.md)) and the CI workflow on GitHub.
* Chromium only; no Firefox/Safari; no screen reader session (axe is automated and catches a fraction of issues).
* Performance was not measured; polling intervals are reasoned, not tuned.

## Deviations from the plan (found while building)

* `strategies` is not a module: the catalogue and its parameter form live in `shared` because `bots` and `backtests` both need them ([02](02-project-structure.md)).
* The backend's overview lacked `mode`, which the UI needs on every bot card (UX-7): added to `GET /bots/overview`.
* Money inputs are plain text fields with validators; lost-ui's money/number inputs hold JavaScript numbers ([L6](lost-ui-requests.md)).
* The profile page is our own (lost-ui's `ProfilePage` requires a name field that does not exist here, [L8](lost-ui-requests.md)).
* Breadcrumbs show "Detalhe" for ids instead of resolving the bot name.
* "Create bot from this backtest" passes the parameters through search params to `/bots/new`.
* No "today's PnL": the backend sends realized PnL since the start only.
* The lost-ui `Stepper` of the live flow is display-only (the flow advances with the buttons).

## Next

* Run the testnet path for real with the owner's own testnet keys, then the live flow with tiny caps, and record the results here.
* Server-side sorting and text search on lists, and a realtime channel, both need backend features first.
* Library requests: [lost-ui-requests.md](lost-ui-requests.md).

## Not planned

Mobile app, WebSocket streaming, password reset by email and MFA (the backend has neither), strategy authoring in the browser, languages other than pt-BR for the app copy.
