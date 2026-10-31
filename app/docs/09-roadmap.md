# 09 — Roadmap

Order of work for the frontend, aligned with what the backend already offers (all backend phases 0–5 are implemented). Each step is one coherent change that ends with the Definition of Done ([08](08-quality.md)); safety-relevant screens come **after** the read-only ones so the operator can watch before they can act.

| Step | Delivers | Depends on | Done when |
|---|---|---|---|
| **F0 Scaffold** | Vite + TanStack Start (SPA mode), TypeScript strict flags, Tailwind 4, `lost-ui` alias + `styles.css` + tokens, ESLint (copied `eslint-local`, module boundaries), Prettier, husky, Vitest, Playwright skeleton, `.env.example`, CI. Copy the `lost-ui` skill and the `.claude` hooks/commands. All "To verify" items of [01](01-stack.md) and [03](03-lost-ui.md) resolved | — | `lint`, `typecheck`, `build` pass on an empty shell; `BackofficeLayout` and `LoginPage` render |
| **F1 API client + session** | `lib/shared/api` (client, `ApiError`, zod boundary), `QueryKey`, `session.ts` (memory token, single-flight refresh), `format.ts`, `dates.ts`, logger | F0 | Unit tests: single-flight, 422 mapping, formatters |
| **F2 Auth** | `/login`, `_app` guard + bootstrap refresh, logout, profile + change password, `can()` and role-aware navigation, error pages | F1 | E2E: login, reload keeps session, logout, viewer vs admin nav, session expiry redirect |
| **F3 Read-only operations** | Safety strip + system status, dashboard, bots list, bot detail (resumo / ordens / sinais / desempenho / configuração / auditoria), audit screen, polling + stale marks | F2 | Watching a running **paper** bot from the browser; stale treatment verified by stopping the worker |
| **F4 Controls (paper)** | Create/edit bot (paper), strategy parameter form, start / pause / stop / reset, desired-vs-observed handling, kill switch (activate / release) | F3 | E2E: create → start → converges → stop; kill switch blocks start |
| **F5 Research** | Market-data coverage + imports, backtests (run, results, train/test, compare), sweeps, charts (equity; price when L1 lands) | F3 | Backtest runs to completion with polling; coverage warns on gaps |
| **F6 Exchanges and testnet** | Connections (create, verification states, disable), testnet bots | F4 | Testnet bot created against a testnet connection (real testnet only with the user's own keys) |
| **F7 Live flow** | Live connection, readiness checklist, promote, typed-name approval with token countdown, start with token, live visual treatment (`--live`, banner) | F6 | Every refusal path rendered verbatim; E2E against the stack **with live disabled** shows the refusals; no real order ever sent from tests |
| **F8 Admin** | Users (create, disable, enable) | F2 | |
| **F9 Hardening** | CSP and headers on the host, accessibility pass, 360 px pass on every screen, performance pass, README, runbook for deploying front + API under one domain | all | Checklist of [07](07-ux-rules.md) passes |

## Parallel backend asks

From [06](06-screens.md#open-requests-to-the-backend-found-while-specifying-the-screens): **R1** portfolio summary (before F3's dashboard totals), **R3** "is live possible" (before F7), **R2** list pagination (before the audit screen is used for real), **R4** capabilities in `/auth/me` (nice to have).

## Library asks (lost-ui)

L1 candlesticks with markers (F5), L3 stat tile (F3), L2 zoom/brush (F5, optional), L4 status dot (F3). Tracked in `docs/lost-ui-requests.md` once the app exists.

## Not planned

Mobile app, WebSocket/streaming (needs a backend feature first), password reset by email and MFA (the backend has neither), multi-exchange comparison dashboards, strategy authoring in the browser (strategies are code on the backend), i18n beyond pt-BR (lost-ui supports en/es/pt; the app copy is pt-BR only).
