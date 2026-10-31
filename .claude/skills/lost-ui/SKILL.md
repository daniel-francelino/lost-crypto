---
name: lost-ui
description: Build UIs with lost-ui, the shared React 19 + Tailwind v4 component library of aura-creative and memoria-print (shadcn primitives, Nuxt UI style elements, forms with rules, DataTable, charts, app layout, ready-made auth/settings/notifications/error pages, i18n en/es/pt). Use when creating or changing a screen, form, table, layout, sidebar, modal, toast, login/sign-up/settings/notifications/error page, or when asked to reuse a component, in any project that depends on lost-ui — before writing a component by hand or copying one from another project.
---

# lost-ui

`lost-ui` is the library the apps share. **Look for the piece in lost-ui before writing or copying one.** If it exists, use it through props. If it almost fits, add the missing prop to the library (see "Changing the library") instead of forking it in the app. Library docs and code are in English; reply to the user in the language they write in.

## Current project context

Before the first change in an app, check (do not assume):

1. `@danielsoaresf/lost-ui` is in the app's `package.json`, and which of its optional peers are installed (`react-day-picker`, `input-otp`, `libphonenumber-js`, `country-flag-icons`, `emoji-picker-react`, `sonner`, `cmdk`, `vaul`, `recharts`, `react-hook-form`, `react-resizable-panels`, `embla-carousel-react`). A component that needs a peer the app lacks needs that peer installed, not a replacement.
2. The app's stylesheet imports `@danielsoaresf/lost-ui/styles.css` and defines the tokens (see [setup](references/setup.md)).
3. Which router the app uses, so you can write `renderLink`, and where its auth/permission helpers are.

## Principles

1. **Use what exists.** Template, then component, then primitive. Never rebuild `AuthShell`, `PageHeader`, `EmptyState`, `SectionCard`, `PasswordField` or an app sidebar.
2. **Props over markup.** Charts, tables, forms and pages are driven by props. Raw Recharts, hand-made tables and hand-validated forms are the last resort.
3. **The app owns data, routes and permissions.** The library receives items and calls handlers. It never fetches, never reads auth, never knows the router.
4. **Semantic tokens only.** `bg-primary`, `text-muted-foreground`. No hex, no raw Tailwind palette.
5. **Look the API up, do not guess it.** Read the props in [references/api/](references/api/) (or the story of the component) before using it.

## Critical rules

Short form; the full list with wrong/right pairs is in [guidelines](references/guidelines.md).

- Wrap the app once in `App` (`@danielsoaresf/lost-ui/app/app`) or `LostI18nProvider` + `Toaster`.
- Forms: `Form` + fields with `rules`; never validate by hand what `rules` covers. Many fields from data: `FormBuilder`.
- Links: pass `renderLink` and the router `pathname` to navigation components.
- Permissions: mark items `hidden` or pass `allow`; do not fork the sidebar.
- Texts: the library brings en/es/pt; the app's own texts go in `registerMessages`. A prop always beats the translation.
- Components with an optional peer are imported **by path** (`@danielsoaresf/lost-ui/forms/form-input-date`, `@danielsoaresf/lost-ui/ui/sonner`, `@danielsoaresf/lost-ui/app/app`…), not from the layer entry.
- Tables: `DataTable` with `getRowId`, server mode via `total`, `manualSort`, `manualSearch`. Do not hand-roll pagination.
- Do not add `motion` code for a page or panel swap: `PageTransition` and `AppShell`'s `transitionKey` exist, and animated parts already respect "reduce motion".

## Which reference to read

Load only what the task needs.

| Task                                                                                   | Read                                                                            |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| first use in an app, styles, peers, import paths                                       | [setup](references/setup.md)                                                    |
| any task: rules, which piece to choose, wrong/right pairs                              | [guidelines](references/guidelines.md)                                          |
| backoffice layout, sign in/up, recover/reset, errors, notifications, settings, profile | [layouts](references/layouts.md) + [api/templates](references/api/templates.md) |
| sidebar, top bar, bottom bar, user menu, header, footer                                | [api/app](references/api/app.md)                                                |
| forms and validation                                                                   | [recipes](references/recipes.md) + [api/forms](references/api/forms.md)         |
| tables, empty states, timeline, tree                                                   | [recipes](references/recipes.md) + [api/data](references/api/data.md)           |
| modal, slideover, chip, kbd, stepper, link, page transition                            | [api/elements](references/api/elements.md)                                      |
| charts                                                                                 | [api/charts](references/api/charts.md)                                          |
| a calendar (month, week, day) with events                                              | [calendar](references/calendar.md) + [api/calendar](references/api/calendar.md) |
| a rich text / block editor like Notion                                                 | [editor](references/editor.md) + [api/editor](references/api/editor.md)         |
| AI chat screen or pieces: messages, prompt, tool calls, streaming                      | [ai-chat](references/ai-chat.md) + [api/ai-chat](references/api/ai-chat.md)     |
| shadcn primitives (button, dialog, select…)                                            | [catalog](references/catalog.md); the props are the shadcn / Radix ones         |
| landing-page effects                                                                   | the library's `docs/effects-inventory.md`                                       |
| "is there a component for X?"                                                          | [catalog](references/catalog.md)                                                |

## Workflow

1. Name the screen and find the piece: template, then component, in the [catalog](references/catalog.md).
2. Read its props in `references/api/<layer>.md` and its story (`<name>.stories.tsx`) for a working example.
3. Compose it from props. Keep data fetching, routes and permissions in the app.
4. If the design needs something the piece lacks, add the prop to the library (below). Do not copy the component into the app.
5. Run the app's own typecheck, lint and tests, and report what failed and what was not run.

## Changing the library

Only when the user asks, or when a missing prop would otherwise force a fork. Work in the lost-ui repo and follow its `CLAUDE.md`: every component has a story and a test in the same change, texts come from `src/i18n` in the three locales, colours from tokens, one component per file; run `npm test` and `npm run typecheck` before saying it is done. Do not edit the generated `index.ts` barrels (`npm run barrels`). After changing props or adding a component, run `npm run skill` so this skill's API reference stays true.

## Limits

- Tested in jsdom: structure and behaviour are proven, layout and pixels are not. Check new screens in the browser or in Storybook.
- `@danielsoaresf/lost-ui/charts` and `@danielsoaresf/lost-ui/forms` are not re-exported from the root entry (they need optional peers).
- Not yet verified inside memoria-print (it uses `@import "tailwindcss" source(none)`): test the Tailwind `@source` there first.
