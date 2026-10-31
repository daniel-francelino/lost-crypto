# Guidelines

## Component or template

A **component** is a piece you place in a screen. A **template** is a page or the frame of one, reused between projects: it takes props and handlers and keeps no data, routes or permissions. A template imports components, never the other way round.

## Which layer

| Need                                              | Layer       |
| ------------------------------------------------- | ----------- |
| a primitive (button, dialog, select, tabs, toast) | `ui`        |
| a small piece (chip, kbd, stepper, modal, link)   | `elements`  |
| part of the frame of an app (sidebar, bars, user) | `app`       |
| a form field or validation                        | `forms`     |
| records, tables, timeline, tree, empty state      | `data`      |
| a chart                                           | `charts`    |
| a whole page or a layout                          | `templates` |
| a landing-page animation                          | `effects`   |

## Which piece

| Task                                         | Use                                                                                 |
| -------------------------------------------- | ----------------------------------------------------------------------------------- |
| internal layout of a backoffice              | `BackofficeLayout` (or `AppShell` + `AppSidebar` + `AppTopbar` + `BottomNav`)       |
| sign in / sign up / recover / reset password | `LoginPage`, `RegisterPage`, `ForgotPasswordPage`, `ResetPasswordPage`              |
| "waiting for approval", "confirm your email" | `AuthMessagePage`                                                                   |
| 404, no permission, broken page              | `NotFoundPage`, `ForbiddenPage`, `ErrorFallback`; full screen: `ErrorPage`          |
| notifications and their preferences          | `NotificationsPage`, `NotificationPreferences`                                      |
| settings area, profile                       | `SettingsLayout`, `SettingsIndexPage`, `SettingsSection`, `ProfilePage`             |
| page title with actions                      | `PageHeader`                                                                        |
| list with sort, search, paging, selection    | `DataTable` + `DataTablePagination`, `DataTableRowActions`, `DataTableColumnToggle` |
| form                                         | `Form` + fields, or `FormBuilder`                                                   |
| password field                               | `FormInputPassword`                                                                 |
| empty list, timeline, tree, user card        | `Empty`, `Timeline`, `TreeView`, `UserInfo`                                         |
| dialog / side panel                          | `Modal` / `Slideover` (props); `Dialog` / `Sheet` for custom content                |
| confirm a destructive action                 | `AlertDialog`                                                                       |
| toast                                        | `toast.success(...)` from `@danielsoaresf/lost-ui/ui/sonner`, `<Toaster />` once    |
| swap a page or a panel with a transition     | `PageTransition`, or `transitionKey` on `AppShell`                                  |
| steps of a wizard                            | `Stepper`                                                                           |
| status label / tag / count                   | `Badge`, `Chip`                                                                     |

## Critical rules

**Colours**

- Wrong: `className="bg-violet-500 text-[#333]"`. Right: `bg-primary`, `text-muted-foreground`, `bg-success/10`. Brand colours are tokens defined by the app.

**Forms**

- Wrong: `useState` + `if (!email.includes("@")) setError(...)`. Right: `<FormInput rules={[rules.required(), rules.email()]} />` inside a `Form`.
- Wrong: a second password field with its own eye icon. Right: `FormInputPassword`.
- Wrong: comparing two fields in `onSubmit`. Right: `rules.matches(() => other)`.
- `Form` calls `onSubmit` only after every rule passed and focuses the first invalid field; do not repeat that.
- Mask a field with `mask="(##) #####-####"` (and `unmask` to keep digits only), not a custom `onChange`.

**Navigation and routers**

- Wrong: importing a router in a library component, or forking `AppSidebar` to use `<Link>`. Right: `renderLink={({ item, children, ...rest }) => <Link to={item.to} {...rest}>{children}</Link>}`.
- Always pass the router's `pathname`, otherwise the active item is read from `window.location` and does not follow client-side navigation.

**Permissions and data**

- Wrong: the library reading a `can()`. Right: `hidden: !can(...)` on the item, or `allow={(item) => ...}`.
- A template's submit handler returns a text to show it as the form error, or nothing when it worked. It may throw: the template shows a generic message.
- Server paging: pass `total`, `page`, `pageSize`, `onPageChange`; sorting and search are `manualSort` / `manualSearch` when the server does them.

**Texts**

- Wrong: hard-coding "Close" or a Portuguese string inside a library component. Right: the key in the three locales of `src/i18n` and `useLostTranslation`.
- In an app: `registerMessages("app", { en, pt })` and `useLostTranslation("app")`.

**Structure**

- Wrong: `<div className="rounded-2xl border p-5">` for a card with title and footer. Right: `Card`, or `SettingsSection`.
- Wrong: a custom empty state. Right: `Empty`.
- Overlays always have a title (`Modal title`, `DialogTitle`); hide it visually, do not omit it.
- Do not set `z-index` by hand on overlays; the primitives handle stacking.

**Motion**

- Wrong: wrapping a page in a new `motion.div`. Right: `PageTransition` / `transitionKey`.
- Animated parts already honour "reduce motion" through `MotionConfig`.

## When the piece does not fit

1. Check the other props and the story: most variants exist.
2. Compose two pieces (e.g. `SettingsSection` + `NotificationPreferences`).
3. Add the prop to the library with a story and a test, then use it.
4. Only if it is truly specific to one app, build it in the app, from lost-ui primitives and tokens, never by copying a lost-ui component.
