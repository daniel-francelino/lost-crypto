# Project decisions

These rules prevail over any document. Detail and rationale: `docs/README.md` (decisions F1–F10), `docs/08-quality.md` (rules and Definition of Done).

- Stack: TanStack Start in **SPA mode** (no server code), Router, Query, React 19, Vite, Tailwind 4, zod 3, `lost-ui`. The only backend is `../api` (FastAPI); the app has no database, secrets or business rules.
- Folders by **module** (`auth`, `bots`, `backtests`, `market-data`, `strategies`, `exchanges`, `system`, `audit`, `shared`) inside `components`, `lib`, `hooks`. A module imports itself and `shared` only. Imports use the `@/` alias, no re-exporting `index.ts`.
- No comments in `src` (only `eslint-disable … -- reason` and `@ts-expect-error`). No `console` (use `logError`, which redacts secrets). No `any`, `!`, `as unknown as`, nested `if`. Strict TypeScript flags stay on.
- No loose text where a constant exists: enums in `lib/shared/enums.ts` (`as const`, `z.nativeEnum`), `QueryKey.*`, `AppRoute.*`, `StoredKey` for browser storage.
- **Money and quantities are decimal strings.** Format only through `lib/shared/format.ts`. Dates only through `lib/shared/dates.ts`; show UTC explicitly for candle and daily-cap times.
- The access token lives in memory only; the refresh token is an httpOnly cookie. Never `localStorage` for credentials. The backend `API_TOKEN` is never used by the app.
- Live trading is never one click: mode is always visible, every live start needs the typed-name approval flow, backend refusals are shown verbatim.
- Colours only through tokens (`bg-primary`, `text-muted-foreground`, `bg-live`…); no hex, no pure black/white, no default Tailwind palette. State never by colour alone.
- Every screen: skeleton → error with retry → empty → no results → data; polled data shows its freshness and a stale mark.
- Language: documentation, code, routes and folders in English; UI copy in Brazilian Portuguese.
