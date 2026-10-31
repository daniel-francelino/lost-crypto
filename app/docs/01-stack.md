# 01 — Stack

Source of the analysis: `aura-creative` (`package.json`, `vite.config.ts`, `tsconfig.json`, `eslint.config.js`, `docs/standards`). Versions below are the ones that project uses today; pin the same ranges at scaffolding and check for newer patch releases then.

## What we adopt

| Concern | Choice | Version in aura-creative | Notes for Lost Crypto |
|---|---|---|---|
| Framework | TanStack Start (`@tanstack/react-start`) | ^1.168 | Used in **SPA mode** (see below) |
| Routing | TanStack Router, file-based | ^1.170 | Generates `routeTree.gen.ts`; typed links and search params |
| Server state | TanStack Query | ^5.104 | All API data; polling; cache keys from a `QueryKey` registry |
| UI library | `lost-ui` (installed as `"lost-ui": "npm:@danielsoaresf/lost-ui@^0.2.2"`) | 0.2.2 | See [03](03-lost-ui.md). Never run a plain `npm i lost-ui` (another package) |
| Styling | Tailwind CSS 4 (`@tailwindcss/vite`) + `tw-animate-css` | ^4.3 | Tokens only, no hex, no raw palette |
| Primitives | Radix UI (arrive through lost-ui's shadcn layer) | | Install only the peers that lost-ui components in use require |
| Forms | lost-ui `Form` + `rules` | | `react-hook-form` is a lost-ui peer for its shadcn `Form`; install it only if needed |
| Validation | zod 3 | ^3.25 | Request bodies built in the app and **API responses** (see [04](04-api-client.md#validating-responses)) |
| Charts | `recharts` (peer of `lost-ui/charts`) | 3.10.1 (pinned) | Pinned exactly in aura; do the same |
| Icons | `lucide-react` | ^0.575 | |
| Toasts | `sonner` (through lost-ui `Toaster`) | ^2 | |
| Dates | `date-fns` + `@date-fns/tz` behind one `dates.ts` | ^4 / ^1.5 | The Date API is banned outside that file |
| Language | TypeScript 5.9, ESM, strict flags (see [08](08-quality.md)) | | |
| Build | Vite 8 | ^8.1 | Static client build, no `nitro` preset (verified in F0: `dist/client/_shell.html` + assets) |
| Unit tests | Vitest 3 | ^3.2 | |
| E2E | Playwright | ^1.64 | |
| Lint / format | ESLint 9 flat config + typescript-eslint + local rules, Prettier 3, husky + lint-staged | | Reuse the `eslint-local/` rules (see below) |
| Node | 22 | CI | |

## What we drop

Supabase (`@supabase/*`), `aws4fetch` (R2), Tiptap and the editor peers, `@dnd-kit/react`, `emoji-picker-react`, `simple-icons`, `nitro`, `@electric-sql/pglite`, the `db:*`, `seed:owner` and `check:docs` (SQL registries) scripts, `vercel.json`, the Vercel cron routes. Add `react-day-picker` only when a date field is built (backtest range, candle import range), and `lost-ui`'s other optional peers only when a component that needs them is imported.

## Rendering mode: client-only (decision F2)

The reasons, in order of weight:

1. **Authentication cannot be server-rendered.** The access token is a JWT held in memory by design; the refresh token is an httpOnly cookie scoped to the **API's** origin and path (`/api/v1/auth`). A Start server on another origin never sees either, so it cannot fetch data on the user's behalf.
2. **There is nothing for a server to do.** No secrets, no database, no file storage. The aura-creative server functions exist for Supabase and R2; Lost Crypto has FastAPI.
3. **The app is private.** SEO and first-paint HTML of a logged-in console have no value.

So: `tanstackStart({ spa: { enabled: true } })` in `vite.config.ts` (verified in F0). `vite build` prerenders only the SPA shell and emits `dist/client/_shell.html` plus assets; `dist/server` is also produced but is not deployed. Route `loader`s and `beforeLoad` run in the browser. Serve `dist/client` as static files with `_shell.html` as the fallback for every path (**To verify** on the real host).

If a server-rendered public page is ever needed (a marketing page, a status page), it is a separate decision recorded here before it is built.

## Environment variables

Only public values, all with the `VITE_` prefix (anything else would be a secret, and the frontend has none):

| Variable | Example | Meaning |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000/api/v1` | Base URL of the backend |
| `VITE_APP_ENV` | `local` \| `prod` | Shows the environment banner; **never** used to enable a feature, the backend decides |

Rules inherited from aura-creative (SEC): no secret ever carries `VITE_`; `.env*` files are not read or printed by tools; `.env.example` lists every variable with a comment. The backend must list the app's origin in `CORS_ORIGINS` (default `http://localhost:5173`).

## Same-site requirement (important for production)

The refresh cookie is `SameSite=Lax`. A cross-origin `fetch` carries it only when the page and the API are **same-site** (same registrable domain): `localhost:5173` → `localhost:8000` works; `app.example.com` → `api.example.com` works; `example.com` → `somethingelse.io` does **not**. Deploy the front and the API under one domain, or behind one reverse proxy. Cookies are `Secure` whenever the backend's `APP_ENV` is not `local`, so production needs HTTPS.

## Tooling reused from aura-creative

* `eslint-local/` — the local rules (`no-comments`, `imports-together`, `no-magic-strings`, `no-literal-zod-enum`, `no-nested-if`) and the per-space import boundaries; copy and adapt, do not rewrite.
* `tsconfig.json` — the strict flag set is a rule (CODE-9): `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noPropertyAccessFromIndexSignature`, `noImplicitReturns`, `noUnusedLocals/Parameters`, `erasableSyntaxOnly`, `verbatimModuleSyntax`.
* `.prettierrc`, `.husky/pre-commit` (lint-staged) and `pre-push` (lint + typecheck + consistency).
* The `.claude/` folder (hooks, `lost-ui` skill, `standards-reviewer` agent, slash commands) once the app has code: copy the `lost-ui` skill as it is — its `references/api/*.md` are the props documentation Claude uses.
