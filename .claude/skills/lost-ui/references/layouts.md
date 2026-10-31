# Layouts and pages

Templates from `@danielsoaresf/lost-ui/templates` (the props of each are in [api/templates](api/templates.md)) and the pieces of `@danielsoaresf/lost-ui/app` they are made of. Every one is router-agnostic (`renderLink`), takes its data as props and reports with handlers. `renderLink` below is `({ item, href: _href, children, ...rest }) => <Link to={item.to} {...rest}>{children}</Link>` with the router of the app.

## Backoffice layout

```tsx
import { BackofficeLayout } from "@danielsoaresf/lost-ui/templates";
import { Link, Outlet, useRouterState } from "@tanstack/react-router";

const renderLink = ({ item, href: _href, children, ...rest }) => (
  <Link to={item.to} {...rest}>
    {children}
  </Link>
);

function AdminLayout() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  return (
    <BackofficeLayout
      sections={navigation} // { label?, items: NavItem[] }[]  (title, icon, to, exact, badge, children, hidden)
      allow={(item) => canSee(item)} // permissions stay in the app
      pathname={pathname}
      renderLink={renderLink}
      logo={<Logo />}
      user={{ name, email, description: role }}
      userItems={[{ title: "My profile", to: "/admin/profile" }]}
      onSignOut={signOut}
      breadcrumbs={crumbs} // { label, to? }[]
      unreadCount={unread}
      notificationsHref="/admin/notifications"
      spaces={spaces} // { id, title, icon, to }[]  (hidden when fewer than 2)
      currentSpace="marketing"
      bottomItems={main}
      moreItems={rest} // the bar of phones; leave out for none
      transitionKey={pathname} // animates the page swap
    >
      <Outlet />
    </BackofficeLayout>
  );
}
```

Need more control? Use `AppShell`, `AppSidebar`, `AppTopbar`, `UserMenu`, `SpaceSwitcher`, `NotificationButton`, `BottomNav` from `@danielsoaresf/lost-ui/app`. `NavItem` helpers: `filterNavigation`, `isNavItemActive`, `flattenNavigation`.

## Auth pages

`LoginPage` is a card with the form on one side and an image on the other (the shadcn "login" block): welcome heading, email, password with "Forgot your password?" on the label line, the sign in button, "Or continue with" icon buttons, the sign up line, and the terms under the card.

```tsx
import { LoginPage } from "@danielsoaresf/lost-ui/templates";

<LoginPage
  description="Login to your Acme Inc account"
  identifier="email" // "text" also takes a username
  identifierPlaceholder="m@example.com"
  forgotPasswordHref="/recover-password"
  registerHref="/register" // registerLabel to rename "Sign up"
  renderLink={renderLink}
  providers={[{ id: "google", label: "Google", icon: <GoogleIcon />, onClick: signInWithGoogle }]}
  legal={
    <>
      By clicking continue, you agree to our <a href="/terms">Terms of Service</a>.
    </>
  }
  aside={
    <img
      src="/login.jpg"
      alt=""
      className="absolute inset-0 size-full object-cover dark:brightness-[0.2]"
    />
  }
  onSubmit={async ({ identifier, password }) => {
    const result = await signIn({ identifier, password });
    if (!result.ok) return errors[result.reason]; // a text is shown as the form error
    router.history.push(redirectTo); // returning nothing means it worked
  }}
/>;
```

Without `aside` it is one narrow card. All the auth pages (`RegisterPage`, `ForgotPasswordPage`, `ResetPasswordPage`, `AuthMessagePage`) share the same `AuthLayout`: the same card, a centred title, the line of links (`footer`) inside the card and the small print (`legal`) under it. `RegisterPage` has the same `providers`, `legal` and `aside` as `LoginPage`, takes `emailHelp` for the text under the email, and shows the password and its confirmation side by side. `variant="card"` (one centred card on a plain page, the footer under it) and `variant="split"` (half of the screen) are still there.

`RegisterPage` (`fields`, `minPasswordLength`, `loginHref`, `onSubmit(values)`), `ForgotPasswordPage` (`onSubmit({ email })`, then shows "check your email"), `ResetPasswordPage` (`onSubmit({ password })`), `AuthMessagePage` (`title`, `description`, `icon`, `actions`).

## Error pages

```tsx
// router errorComponent / notFoundComponent, inside the layout
<ErrorFallback onRetry={reset} homeHref="/admin" renderLink={renderLink} />
<NotFoundPage homeHref="/admin" renderLink={renderLink} />
<ForbiddenPage homeHref="/admin" renderLink={renderLink} />
```

For a screen of its own (public site): `ErrorPage` from `@danielsoaresf/lost-ui/app/error-page` with `error={{ statusCode, message }}`.

## Notifications page

```tsx
<NotificationsPage
  notifications={items} // { id, title, body?, createdAt, readAt?, severity?, kind? }[]
  loading={isLoading}
  error={isError}
  onRetry={refetch}
  unreadCount={unread}
  onReadAll={readAll}
  onOpen={open}
  onRead={read}
  onSnooze={snooze}
  filter={filter}
  onFilterChange={setFilter} // "all" | "unread" | "snoozed"
  kinds={kinds}
  kind={kind}
  onKindChange={setKind}
  hasMore={items.length < total}
  loadingMore={isFetching}
  onLoadMore={more}
/>
```

Preferences: `<SettingsSection title="Notifications"><NotificationPreferences preferences={rows} onChange={(kind, channels) => save(kind, channels)} /></SettingsSection>`.

## Settings and profile

```tsx
<SettingsLayout items={settingsTabs} pathname={pathname} renderLink={renderLink}>
  <Outlet />
</SettingsLayout>

<SettingsIndexPage entries={entries.filter(can)} renderLink={renderLink} />   // entries: NavItem + description

<ProfilePage
  name={profile.name}
  description={`@${profile.username} · ${email}`}
  onSaveName={async (name) => (await save(name)).ok ? undefined : "Could not save."}
  onChangePassword={async ({ password }) => update(password)}
>
  {/* extra sections, e.g. notification preferences */}
</ProfilePage>
```
