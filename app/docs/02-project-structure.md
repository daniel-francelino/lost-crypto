# 02 — Project structure

Adapted from aura-creative's "type → space → module" rule. Lost Crypto has one audience (the operator), so the middle level is dropped: **type → module**.

## Layout

```
app/
  docs/                          these documents
  e2e/                           Playwright flows
  eslint-local/                  local lint rules (copied from aura-creative)
  public/
  src/
    components/<module>/         screen pieces of one module
    components/shared/           pieces used by more than one module
    hooks/<module>/  hooks/shared/
    lib/<module>/    lib/shared/ schemas, types, query keys, API calls, formatting
    routes/                      TanStack file routes (assemble screens only)
    router.tsx · routeTree.gen.ts · styles.css
```

### Modules

They mirror the backend modules, so a backend change has an obvious frontend home.

| Module | Backend area | Contents |
|---|---|---|
| `auth` | `/auth/*` | session store, login/logout/refresh, users admin |
| `bots` | `/bots/*` | list, detail, create/edit, controls, live promotion and approval |
| `backtests` | `/backtests/*` | run form, results, sweeps, compare |
| `market-data` | `/market-data/*` | coverage, imports, candles |
| `exchanges` | `/exchange-connections/*` | connections page and creation form (the read side lives in `shared`, see below) |
| `system` | `/system/*`, `/alerts` | the *Status* page and the *Alertas* page (the safety strip, the alerts indicator and the kill switch are in `shared/layout`; the alerts data layer is in `shared`) |
| `audit` | `/audit-events` | event log |
| `shared` | — | API client, `ApiError`, enums, query keys, formatting, dates, layout wiring, hooks used by 2+ modules |

**What lives in `shared` and why.** Several modules need the same read-only catalogues, so they cannot sit in one of them: the strategy catalogue and its parameter form (`lib/shared/strategies`, `components/shared/strategy`; used by `bots` and `backtests`), the list of connections (`lib/shared/exchanges`; used by `bots` and `exchanges`), market-data coverage (`lib/shared/market-data`), system status/capabilities/kill switch (`lib/shared/system`; used by the shell and every live-sensitive screen), the audit table (`components/shared/audit`; used by the audit screen and the bot tab), metrics/equity pieces, status badges, `ConfirmDialog`, form validators. This is why `strategies` is **not** a module here although it is a backend module. ESLint enforces the boundary: `bots`, `backtests`, `market-data`, `exchanges`, `system`, `audit`, `auth` import only themselves and `shared`.

`shared` is a module like the others in the tree (`components/shared`, `lib/shared`, `hooks/shared`).

## Who may import whom

```
              shared
   ↗    ↗     ↑     ↖    ↖
 bots backtests exchanges system …   (modules)
```

* A module imports from **itself and `shared`** only. Two modules that need the same piece move it to `shared` (never copy it, never open an exception).
* **Routes import from every module**; they assemble screens. Cross-module screens (the dashboard shows bots, system status and the kill switch) live in `routes/` as thin compositions of module components, or in a `dashboard` module that is explicitly allowed to import from the others (decide when it is built, then record it here and in ESLint).
* Imports always use the `@/` alias; a relative path only inside the same module; no re-exporting `index.ts`.
* Enforced by `no-restricted-imports`, one block per module in `eslint.config.js`, so a violation is a lint error.

Why modules cannot import each other: it keeps `bots` from quietly depending on how `backtests` fetches data. The one cross-module relation that is real — a bot is created from a backtest or strategy choice — goes through route params and `shared` types, not through imports.

## Routes

```
src/routes/
  __root.tsx                       providers (lost-ui App, QueryClient), error boundary
  login.tsx                        public
  _app.tsx                         authenticated shell: guard + BackofficeLayout
  _app/
    index.tsx                      dashboard (overview + system status)
    bots/index.tsx · bots/new.tsx · bots/$botId.tsx
    backtests/index.tsx · backtests/new.tsx · backtests/$runId.tsx · backtests/compare.tsx
    backtests/sweeps/$sweepId.tsx
    market-data/index.tsx          coverage + imports
    exchanges/index.tsx · exchanges/new.tsx
    audit/index.tsx
    system/index.tsx
    settings/profile.tsx · settings/users.tsx
```

* `_app` is a pathless layout: its `beforeLoad` ensures a session (see [05](05-authentication.md)) and redirects to `/login?redirect=…`.
* **One folder per module with `index.tsx`, `new.tsx` and `$id.tsx`**; the file only wires guard, search params and the page component imported from `components/<module>`. No business logic or JSX beyond that component.
* Search params (filters, sort, tab, range) live in the URL and are validated with zod (`validateSearch`); changing a filter resets paging.
* A route name that is not in the table above is added here first.

## Naming

| Thing | Convention | Example |
|---|---|---|
| Files, folders | kebab-case, English | `bot-controls.tsx`, `market-data/` |
| Components | PascalCase export, one main component per file | `BotControls` |
| Hooks | `use-*.ts` | `use-bot-overview.ts` |
| API calls | `<module>.api.ts` in `lib/<module>/`, verbs: `listBots`, `startBot` | `bots.api.ts` |
| Schemas, types | `schemas.ts`, `types.ts` per module; schema names end in `Schema` | `botSchema` |
| Constants | `PascalCase` object `as const` + same-name type; never TS `enum`, never `z.enum([...])` (use `z.nativeEnum`) | `BotState`, `ExecutionMode` |
| Query keys | `QueryKey.<Module>.<name>(…)` | `QueryKey.Bots.detail(id)` |
| Stored browser values | one `StoredKey` registry with `readStored` / `writeStored` | never raw `localStorage` |
| Tests | `*.test.ts` next to the file; E2E in `e2e/<flow>.spec.ts` | |
| Commits | Conventional Commits, scope = module | `feat(bots): add live approval dialog` |

**Where does a new file go?** (1) What type is it? component / hook / lib / route. (2) Who uses it? One module → that module; two or more → `shared`. (3) Reuse the module folder. (4) Does an equivalent exist? Extend it.
