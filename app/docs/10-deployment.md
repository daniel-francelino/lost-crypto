# 10 — Deployment and hardening

The app builds to static files. This document is what to configure around them. **Nothing here was deployed or tested on a real host**; the headers below are a checked-in recipe, not a verified setup.

## Build

```bash
cd app
npm ci
VITE_API_BASE_URL=https://api.example.com/api/v1 VITE_APP_ENV=prod npm run build
```

Deploy `dist/client/` (assets + `_shell.html`). `dist/server/` is not deployed. Every path must fall back to `_shell.html` (it is a single-page app; deep links such as `/bots/<id>` are resolved in the browser). Cache `assets/*` for a long time (file names are hashed) and `_shell.html` with `no-cache`.

`VITE_*` values are baked into the bundle at build time and are public. A `prod` build pointing at a local API (or the reverse) shows a blocking banner in the shell (UX-14).

## Docker

`app/Dockerfile` builds the app and serves `dist/client/` with nginx (`app/nginx.conf`: SPA fallback to `_shell.html`, long cache for `assets/`, `no-cache` for the shell) on port 5173. `VITE_API_BASE_URL` and `VITE_APP_ENV` are build arguments. The root `docker-compose.yml` runs it together with the backend (`make up` at the repo root). Checked locally: the container answers 200 on `/` and on a deep link, and the API returns the CORS headers for `http://localhost:5173`. It sends only `Referrer-Policy`, `X-Content-Type-Options` and `X-Frame-Options`; the CSP below is not applied because it was not loaded against the app yet.

## Same-site requirement

The refresh token is a `SameSite=Lax`, `HttpOnly`, `Secure` cookie on the **API** origin (`Path=/api/v1/auth`). The browser sends it on `fetch` calls from the app only when both are **same-site**:

| App | API | Works |
|---|---|---|
| `https://app.example.com` | `https://api.example.com` | yes (same registrable domain) |
| `https://example.com/` | `https://example.com/api/v1` (one reverse proxy) | yes (same origin, no CORS needed) |
| `https://example.com` | `https://other-domain.io` | **no**: login works, every refresh answers 401 |

Backend settings for production: `APP_ENV=prod`, `JWT_SECRET` (≥ 32 chars), `CORS_ORIGINS` = the exact app origin (a JSON list, e.g. `["https://app.example.com"]`), HTTPS in front. The cookie endpoints also check `Origin` against `CORS_ORIGINS`; a mismatch is a 403.

## Security headers

Set on the static host for the app (not on the API):

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://api.example.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Permissions-Policy: camera=(), microphone=(), geolocation=()
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

Notes to verify on the first real deploy:

* `style-src 'unsafe-inline'` is there because the UI libraries (Radix, Recharts, motion) set inline `style` attributes. Check whether the build also needs inline **scripts** (TanStack Start's SPA shell may inline a small bootstrap script); if it does, prefer a nonce/hash over `'unsafe-inline'` for scripts. Do not ship a policy you have not loaded the app under.
* `connect-src` must list the API origin (and nothing else). The app calls no third-party services and loads no remote fonts.
* No `dangerouslySetInnerHTML` exists in the code base; API strings are rendered as text.

## Example (nginx, not verified)

```nginx
server {
  listen 443 ssl;
  server_name app.example.com;
  root /srv/lost-crypto-app;

  add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https://api.example.com; frame-ancestors 'none'" always;
  add_header Referrer-Policy "no-referrer" always;
  add_header X-Content-Type-Options "nosniff" always;

  location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable"; }
  location / { try_files $uri /_shell.html; add_header Cache-Control "no-cache"; }
}
```

## Operator runbook

1. **First admin:** `docker compose exec api python -m manage create-user <name> --role admin` (prompts for the password; ≥ 12 characters). Further users are created in *Configurações → Usuários*.
2. **Forgot password:** there is no reset by email. An operator with host access creates a new user, or changes the password through the database/`manage`.
3. **Sessions:** changing a password signs the user out everywhere; disabling a user revokes their refresh tokens (their current access token lasts up to 15 minutes).
4. **Kill switch:** reachable from the top bar of every screen. Releasing it does not restart bots.
5. **Going live** is deliberately not a deployment step: see the backend's [doc 13](../../api/docs/architecture/13-live-trading.md). The UI shows the missing switches under *Status*.

## Checks that exist today

| Check | Command |
|---|---|
| Lint, types, formatting, constants vs OpenAPI | `npm run lint && npm run typecheck && npm run format:check && npm run check:consistency` |
| Unit tests | `npm run test` |
| Build | `npm run build` |
| End to end + accessibility (axe, WCAG 2 A/AA, light and dark) | `E2E_ADMIN_USER=… E2E_ADMIN_PASSWORD=… E2E_VIEWER_USER=… E2E_VIEWER_PASSWORD=… npm run e2e` against the Compose stack started with `JWT_SECRET` and `CORS_ORIGINS` containing `http://localhost:5199` |
| Dependency audit | `npm audit --omit=dev --audit-level=high` (CI) |
