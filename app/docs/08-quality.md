# 08 — Quality

The rules are aura-creative's `docs/standards/base.md` (section 3 code rules, 8 interface rules, 10 Definition of Done), minus what only applies to Supabase. Where a rule has an ID there it keeps it; Lost Crypto adds nothing that contradicts it. If the two ever diverge, this file says so.

## Code rules (enforced by ESLint and `tsc`)

| ID | Rule |
|---|---|
| CODE-1 | **No comments in `src`** (not even JSDoc). Only `eslint-disable … -- reason` and `@ts-expect-error`. Express intent with names, types, small functions. (This documentation is where explanations live.) |
| CODE-2 | **No `console`.** Use `logError` from `lib/shared/logger.ts` (which never logs secrets, tokens or request bodies) |
| CODE-3 | Imports in a single block; inline `type` imports; `@/` alias; relative paths only inside one module; no re-exporting `index.ts` |
| CODE-4 | **No loose strings where a constant exists**: `QueryKey`, `StoredKey`, `BotState`/`ExecutionMode`/`OrderStatus`…, `Capability`, route paths via typed `Link`/`to`. `z.nativeEnum`, never `z.enum([...])` |
| CODE-5 | No `any`, no `!`, no `as unknown as`. Type the source or validate it with zod |
| CODE-6 | No nested `if`: guard clauses and early returns |
| CODE-7 | Small functions; components under 600 lines; data/logic in hooks, components presentational |
| CODE-9 | Strict TS flags stay on (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noPropertyAccessFromIndexSignature`, `noImplicitReturns`, `noUnused*`, `erasableSyntaxOnly`, `verbatimModuleSyntax`) |
| CODE-12 | A new dependency needs a reason in the commit message; do not add a library for something lost-ui already does |
| CODE-13 | Prettier formats (width 100, double quotes, semicolons, trailing commas) |
| CODE-14 | No lint-disable to silence a rule without `-- reason`; the exception lists start empty and only shrink |
| MONEY-1 | No `Number()`, `parseFloat`, unary `+` or arithmetic on an API decimal string. The type is the guard (money is `string`); only `lib/shared/format.ts` and the chart helpers may convert, and ESLint (`no-restricted-syntax` for `parseFloat` and `Number(`) is switched off for those files only |
| DATE-1 | The Date API is banned outside `lib/shared/dates.ts` and tests (`no-restricted-syntax`) |
| SEC-1 | No `VITE_` variable holds a secret; no token/credential in `localStorage`, URLs, logs or error reports; no `dangerouslySetInnerHTML` |

## Testing

| Level | Tool | What to cover | Not covered |
|---|---|---|---|
| Unit | Vitest | `format.ts` (decimal strings, rounding, negatives, zero, very small/large), `dates.ts`, session single-flight (one refresh for N concurrent 401s), `ApiError` mapping (422 array → fields), zod schemas against **recorded real responses**, `can()` | layout |
| Component | Vitest + Testing Library (jsdom) | forms (rules, 422 mapping, double submit), the live-approval flow (typed name, token expiry, refusal shown verbatim), stale marks, kill-switch dialog | pixels |
| End-to-end | Playwright against the **real backend** in Docker (`make up`) with a seeded admin and viewer | login → refresh on reload → logout; viewer cannot see write controls; create paper bot → start → observed state follows; kill switch blocks start; backtest run polls to completion; live flow stops at the first refused safeguard (live is off by default in the stack) | real exchanges |
| Contract | CI step | Regenerate types from `api/docs/openapi.json` and fail on a diff; zod schemas must parse fixtures captured from the API | |

* **Never run E2E against a live-enabled stack or with real exchange keys.** The E2E stack runs with `LIVE_TRADING_ENABLED=false`, as the backend defaults.
* Mock the network in unit tests with a small fake `fetch` at the client boundary; do not mock lost-ui.
* Every bug fixed gets a regression test at the lowest level that reproduces it.

## Commands

| When | Command |
|---|---|
| After editing | `npm run lint` · `npm run typecheck` · `npm run format:check` |
| Before pushing (husky `pre-push`) | lint + typecheck + `npm run check:consistency` (compares `src/lib/shared/enums.ts` with the enums of the backend's `openapi.json`) |
| Hooks | The repository root is `lost-crypto`, so husky is installed from `app/` with `core.hooksPath` = `app/.husky/_`; the hooks only act when files under `app/` are staged/pushed |
| Tests | `npm run test` · `npm run e2e` |
| Build | `npm run build` (static SPA output) |
| Contract | `npm run api:types` (regenerates types from `../api/docs/openapi.json`) |

Same scripts as aura-creative, minus `db:*`, `seed:owner`, `check:docs` (replace with a docs-link checker if useful). `lint` runs with `--max-warnings 0`.

## CI (GitHub Actions, adapt aura's `ci.yml`)

`npm ci` → `lint` → `typecheck` → `format:check` → `check:consistency` → `test` → `build` → `npm audit --omit=dev --audit-level=high`. The E2E job brings up the backend with Compose, runs migrations (`alembic upgrade head`), creates the test users through `manage`, and runs Playwright. The existing backend workflow ([`.github/workflows/api-ci.yml`](../../.github/workflows/api-ci.yml)) is separate; add `app-ci.yml` path-filtered to `app/**`.

## Definition of Done (per change)

**Specification**
- [ ] The screen/behaviour is described in [06](06-screens.md) and the rules that apply are known; no name was invented outside the docs or `openapi.json`.
- [ ] Documents touched by the change are updated in the same change; "To verify" items resolved by this change are rewritten as facts.

**Code**
- [ ] Reused an existing piece: lost-ui first, then `shared`. No parallel implementation.
- [ ] CODE-1…CODE-14, MONEY-1, DATE-1, SEC-1 hold; files in the right module; no forbidden cross-module import.

**Interface**
- [ ] Skeleton, error with retry, empty, no results, data; stale handling for polled data (UX-1).
- [ ] Permissions reflected in nav, route, controls (and a 403 handled).
- [ ] Mode (paper / testnet / live) visible wherever a bot or order appears (UX-7).
- [ ] 360 px, tablet, desktop checked in a browser; keyboard works; no colour-only meaning.

**Verification**
- [ ] `lint`, `typecheck`, `test` pass; relevant component/E2E tests added.
- [ ] You can say exactly what was **not** verified (real exchange behaviour, other browsers, real fills).

## Honest limits

* The frontend inherits the backend's unverified areas: live order fills/fees/stops and the exchange's API-permission response were never exercised against real Binance (backend doc 13). A UI flow that "works" against the simulated stack proves the screens, not trading.
* lost-ui is tested in jsdom, so layout is checked by hand.
