# 03 — Using lost-ui

`lost-ui` (`@danielsoaresf/lost-ui`) is the shared React 19 + Tailwind 4 library: shadcn primitives, Nuxt-UI-style elements, forms with rules, `DataTable`, charts, app layout, ready-made auth/settings/notifications/error pages, i18n (en/es/pt). aura-creative installs it under the short alias `lost-ui` and ships a skill with the full props reference; Lost Crypto does the same.

**Rule (aura CLAUDE.md item 10, kept):** look in lost-ui before writing a component. If it exists, use it through props. If it almost fits, ask for the prop in the library. Build in the app only what is truly specific, from lost-ui primitives and tokens — never by copying a library component.

The props are **not** repeated here. They are in the skill: copy `aura-creative/.claude/skills/lost-ui/` into `app/.claude/skills/lost-ui/` and read `references/api/<layer>.md` (generated from the library code) before using a component.

## Principles that matter most

1. The app owns **data, routes and permissions**. The library receives items and calls handlers; it never fetches, reads auth or knows the router.
2. **Semantic tokens only** (`bg-primary`, `text-muted-foreground`, `bg-success/10`). No hex, no Tailwind palette, no arbitrary colours.
3. **Props over markup.** Tables, forms, charts and pages are driven by props.
4. Components with an optional peer are imported **by path** (`lost-ui/forms/form-input-date`, `lost-ui/ui/sonner`, `lost-ui/app/app`), not from the layer entry. `lost-ui/charts` and `lost-ui/editor` are never in the root entry.

## Setup

`src/styles.css`:

```css
@import "tailwindcss";
@import "tw-animate-css";
@import "lost-ui/styles.css";      /* token mapping, no brand values; declares its own @source */
/* the app defines the token VALUES below */
```

* Define the tokens in `:root` and `.dark`: `--background`, `--foreground`, `--card`, `--popover`, `--primary`, `--secondary`, `--muted`, `--accent`, `--destructive`, `--success`, `--warning`, `--info` (each with `-foreground`), `--border`, `--input`, `--ring`, `--radius`, `--header-height`, `--container-width`, plus sidebar tokens. Fonts: `--font-sans`, `--font-display`. Dark mode = the `.dark` class on an ancestor.
* Do **not** import `effects.css` (landing-page animations): there is no landing page. aura keeps a palette document (`standards/color-palette.md`) with AAA body-text contrast; Lost Crypto writes its own `docs/` palette note when the theme is defined (the F0 theme in `src/styles.css` is a neutral blue placeholder, not a brand decision; contrast is unmeasured).
* **Trading semantics need tokens, not ad-hoc colours.** Define and document `--success` (profit / buy), `--destructive` (loss / sell / kill switch), `--warning` (paused / stale / paper-vs-live caution), and one dedicated, unmistakable token for **live mode** (e.g. `--live`) so the same colour is never used for anything else. State is never conveyed by colour alone (see [07](07-ux-rules.md)).

Wrap the app once, in `__root.tsx`:

```tsx
import { App } from "lost-ui/app/app";        // needs sonner
<App language="pt">{/* router outlet */}</App>
```

`App` joins the i18n provider, tooltip provider and `Toaster`. The library ships pt; the app's own texts go in `registerMessages("app", { pt })` and `useLostTranslation("app")`. A prop always beats a translation. UI copy is Brazilian Portuguese ([07](07-ux-rules.md#copy)).

### Peers to install, by need

| Needed for | Peer |
|---|---|
| Toasts, `App` | `sonner` |
| Any chart (equity, drawdown, comparison) | `recharts` (pin the version aura pins) |
| Date fields (backtest range, import range) | `react-day-picker` |
| Command palette / drawers (optional) | `cmdk`, `vaul` |
| Shadcn `Form` primitive | `react-hook-form` |

Do not install `input-otp`, `libphonenumber-js`, `country-flag-icons`, `emoji-picker-react`, the editor (Tiptap) or the carousel/resizable peers until a screen needs them.

## Which piece for which need

| Need in Lost Crypto | Use | Notes |
|---|---|---|
| Authenticated frame: sidebar, top bar, breadcrumbs, user menu, mobile bar | `BackofficeLayout` (`templates`) | `sections`, `pathname`, `renderLink` (TanStack `Link`), `user`, `onSignOut`, `breadcrumbs`, `transitionKey={pathname}`. Hide items with `hidden` / `allow`, never fork the sidebar. No `spaces` prop (one space) |
| Login | `LoginPage` | `identifier="text"` (the backend logs in by **username**), no `registerHref`, no providers, no forgot-password link (no password reset exists). `onSubmit` returns an error text on failure |
| Not found / forbidden / crash | `NotFoundPage`, `ForbiddenPage`, `ErrorFallback` | Router `notFoundComponent`, `defaultErrorComponent`, forbidden redirect |
| Page title + actions | `PageHeader` | Primary action at top right |
| Tables of bots, orders, trades, runs, audit, imports, users | `DataTable` | `getRowId`; sorting client-side on the already-loaded rows (the API has no server sort); see [04](04-api-client.md#lists) |
| Empty list / no results | `Empty` | |
| Forms | `Form` + fields with `rules` | Never hand-validate what `rules` covers. `rules.required()`, `email()`, `minLength()`, `matches()` |
| Strategy parameters form | `FormBuilder` | Fields built from the strategy's parameters delivered by `GET /strategies` (`name`, `type`, `default`, `minimum`, `description`; there is no maximum, the backend validates the rest and answers 422) |
| Money / quantity inputs | `FormInputMoney`, `FormInputNumber` | Value stays a **string**; see [04](04-api-client.md#money-and-numbers) |
| Select, switch, radio, slider | `FormSelect`, `FormSwitch`, `FormRadioGroup`, `FormSlider` | |
| Secrets (API key / secret) | `FormInputPassword` | Plus the handling rules of [05](05-authentication.md#exchange-keys) |
| Confirm a destructive or irreversible action | `AlertDialog`; for typed confirmation, `Modal` with a `FormInput` and `rules.matches` | Kill switch, stop, reset portfolio, promote to live |
| Dialog / side panel | `Modal` / `Slideover` | Overlays always have a title |
| Toasts | `toast.success/error` from `lost-ui/ui/sonner` | Success toast **after** the API confirms |
| Status labels | `Badge`, `Chip` | Bot state, order status, mode, connection status |
| Cards / grouped settings | `Card`, `SettingsSection` | Not a hand-made rounded `div` |
| Charts | `AreaChart` (equity, drawdown), `LineChart` (price, comparison), `BarChart` (sweep results, PnL by period), `PieChart` (allocation) | Data-driven: `data`, `xKey`, `series`. See the missing-piece list below |
| Notifications | `NotificationButton` / `NotificationsPage` | Only if a notification feed is added; the backend has none today |
| Profile + change password | `ProfilePage` | `onChangePassword` → `POST /auth/change-password` |
| Timeline | `Timeline` | Audit trail of one bot |
| Stepper | `Stepper` | Live promotion checklist flow |
| Loading | `Skeleton` | Skeletons keep the layout height |
| Page swap animation | `PageTransition` / `transitionKey` | Do not write `motion` code |

## What lost-ui does not have yet (file a request, do not rebuild)

Keep these in a single `docs/lost-ui-requests.md` (aura's pattern: one table, each request with the app's workaround and a status, updated in place). Initial candidates, to be confirmed against the library when the first chart screen is built:

| ID | Request | Workaround until done |
|---|---|---|
| L1 | **Candlestick (OHLC) chart** with trade markers (buy/sell arrows) and optional indicator overlays (EMA lines, Donchian channel) | `LineChart` of close price with the markers drawn as a second series |
| L2 | **Chart zoom / range brush** for long equity curves | Fetch a bounded range and let the user pick the range with a form |
| L3 | **Stat tile / KPI card** with value, delta and sign colouring | `Card` with typography; no reusable piece |
| L4 | **Live status dot** with accessible label (pulsing "worker alive") that honours reduced motion | `Badge` with text |

Add prop-level requests the same way (a column type for decimal strings in `DataTable`, a `tone` per row, …).

## Verified in F0, and what still is not

* `lost-ui` 0.2.2 installs from npm under the alias; `BackofficeLayout`, `LoginPage`, `PageHeader`, `Empty`, `ErrorFallback`/`NotFoundPage` and `App` render with TanStack's `renderLink` in client-only mode; Tailwind picks the library classes with the default `@source` (checked in Chromium at 1280 px and 360 px, no horizontal overflow).
* The version-matched skill ships inside the package: `node_modules/lost-ui/skills/lost-ui` is copied to `.claude/skills/lost-ui` (re-copy it after upgrading the library; it differs slightly from aura-creative's older copy).
* **Not verified:** colour contrast of the tokens in `src/styles.css` (light and dark, including `--live`), dark mode, and every component not used yet. The library's own tests run in jsdom, so layout is checked by hand in a browser for every new screen.
