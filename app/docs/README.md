# Lost Crypto — Frontend documentation

The operator console of Lost Crypto: a single-user (or few-operator) web app to configure and watch trading bots, run backtests, manage exchange connections and operate the kill switch. It talks **only** to the FastAPI backend in [`../../api`](../../api/README.md); it has no database, no server-side secrets and no business rules of its own.

The stack is the one of the sibling project `aura-creative` (TanStack Start, React 19, Tailwind 4, zod) and the UI comes from the shared library **`lost-ui`**. This documentation is the result of reading that project and its standards; where Lost Crypto differs, the difference is written down in [Deviations](#deviations-from-aura-creative).

> **Status: documentation only.** No frontend code exists yet. Everything here is a decision or a plan, and says so where something still has to be verified when the app is scaffolded.

## Map

| # | Document | Read it to know |
|---|---|---|
| 01 | [Stack](01-stack.md) | What we adopt from aura-creative, what we drop, versions, rendering mode |
| 02 | [Project structure](02-project-structure.md) | Folders by module, who may import whom, routes, naming |
| 03 | [Using lost-ui](03-lost-ui.md) | Setup, theme tokens, which piece for which screen, what is missing from the library |
| 04 | [API client](04-api-client.md) | Calling the backend: base URL, errors, money as strings, polling, query keys |
| 05 | [Authentication and permissions](05-authentication.md) | Login, token in memory, refresh cookie, 401 handling, roles, route guards |
| 06 | [Screens](06-screens.md) | Every screen: route, endpoints, lost-ui pieces, states, permissions |
| 07 | [UX rules for a trading console](07-ux-rules.md) | Live-money safeguards in the UI, state coverage, money/date display, accessibility |
| 08 | [Quality](08-quality.md) | Code rules, lint, tests, CI, Definition of Done |
| 09 | [Roadmap](09-roadmap.md) | Build order, aligned with the backend phases |

Backend references the frontend depends on: [14 — Authentication](../../api/docs/architecture/14-authentication.md), [13 — Live trading](../../api/docs/architecture/13-live-trading.md), [`openapi.json`](../../api/docs/openapi.json) (also served at `/docs` by the running API).

## Decisions

| # | Decision | Why |
|---|---|---|
| F1 | TanStack Start + Router + Query, React 19, Vite, Tailwind 4, zod 3 — the aura-creative stack | One stack across the author's projects; the rules and lint config can be reused |
| F2 | **Client-rendered (Start's SPA mode); no server functions** | The access token lives in memory and the refresh cookie belongs to the API origin, so a server render cannot be authenticated. All data comes from FastAPI, so there is nothing for a Start server to do |
| F3 | UI = `lost-ui` first; app-specific components only when the library has nothing (and a request is filed) | Same rule as aura-creative |
| F4 | Folders by **module** (`bots`, `backtests`, …) mirroring the backend modules; modules never import each other, shared code goes to `shared` | Same idea as aura's "spaces", enforced by ESLint |
| F5 | The frontend **never computes money**. Amounts are decimal strings from the API and are only formatted | Floating point must not touch capital, fees or PnL |
| F6 | The access token is kept in memory only; the refresh token is an httpOnly cookie the script cannot read | Backend design (doc 14); XSS cannot steal a session |
| F7 | `API_TOKEN` (the static service token) is **never** used or stored by the frontend | It is an admin credential for scripts |
| F8 | Live trading is visibly different in the UI (mode badge, colour, typed confirmation) and every start of a live bot needs a fresh approval | Mirrors the backend safeguards; the UI must not make a real-money action look routine |
| F9 | Documentation and code in English, UI copy in Brazilian Portuguese | Same convention as aura-creative |
| F10 | Real-time = polling with TanStack Query; no WebSocket | The backend has none; bots act on candle close (minutes), so seconds-level polling is enough |

## Deviations from aura-creative

| aura-creative | Lost Crypto | Reason |
|---|---|---|
| Supabase (Auth, Postgres, RLS), Cloudflare R2, Resend, Turnstile, Instagram, Vercel cron | None of them | Backend is FastAPI + Postgres; no files, emails or social integrations |
| Server functions (`*.functions.ts`), `Result<T>`, `requireActionServer` | A typed HTTP client in `lib/shared/api` and `ApiError` | There is no server side in the front |
| Permissions = actions per profile × brand link (`has_action`, `Action.Module.Verb`) | Two roles, `admin` and `viewer` | That is the backend's model; see [05](05-authentication.md) |
| Spaces `marketing / cms / site / portal` | Modules only | One audience |
| Server-side pagination on every list (UI-1) | Lists use `limit` (the API has no offset) | The API returns bounded lists; see [04](04-api-client.md#lists) |
| Public site, CMS, SEO, sitemap | None | Not applicable |
| Own `StatusBadge`, `SectionCard`, `ConfirmDialog` kit in `shared/admin` | `lost-ui` only | The library now covers them (aura's `CLAUDE.md` item 10 already says so) |

## Keeping these documents true

* A document changes in the same change as the code it describes (aura rule DOC-2).
* A name (route, query key, enum, error code) that is not in these documents or in the backend `openapi.json` is added to the document first.
* Anything in these documents marked **To verify** must be confirmed when the app is first scaffolded, then rewritten as fact.
