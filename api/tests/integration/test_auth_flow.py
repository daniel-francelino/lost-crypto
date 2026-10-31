"""The login flow a frontend will use, against a real PostgreSQL."""

from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
import pytest
from sqlalchemy import text

from container import Container
from core.config import Settings
from main import create_app
from modules.auth.domain import Role

pytestmark = pytest.mark.integration

PASSWORD = "correct horse battery staple"
SECRET = "j" * 48
SERVICE_TOKEN = "service-token-for-scripts"
ORIGIN = "http://localhost:5173"  # the default CORS origin: where the frontend runs


@dataclass
class AuthEnv:
    app: Any
    container: Container

    def client(self) -> httpx.AsyncClient:
        """A fresh browser: its own cookie jar."""
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://test",
            headers={"Origin": ORIGIN},
        )

    async def make_user(self, name: str, role: Role = Role.ADMIN, password: str = PASSWORD) -> None:
        await self.container.auth.create_user(f"itest-{name}", password, role, actor="test")

    async def login(self, client: httpx.AsyncClient, name: str, password: str = PASSWORD) -> Any:
        return await client.post(
            "/api/v1/auth/login", json={"username": f"itest-{name}", "password": password}
        )

    async def sql(self, statement: str, **params: Any) -> None:
        async with self.container.engine.begin() as conn:
            await conn.execute(text(statement), params)


async def _cleanup(env: AuthEnv) -> None:
    await env.sql(
        "DELETE FROM refresh_tokens WHERE user_id IN "
        "(SELECT id FROM users WHERE username LIKE 'itest-%')"
    )
    await env.sql("DELETE FROM users WHERE username LIKE 'itest-%'")
    await env.sql("DELETE FROM audit_events WHERE entity_type = 'user'")


@pytest.fixture
async def auth_env() -> AsyncIterator[AuthEnv]:
    settings = Settings(  # type: ignore[call-arg]
        jwt_secret=SECRET,
        api_token=SERVICE_TOKEN,
        refresh_reuse_grace_seconds=0,  # make token reuse detectable instantly
        login_max_failures=3,
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        env = AuthEnv(app, app.state.container)
        await _cleanup(env)
        yield env
        await _cleanup(env)


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_login_returns_an_access_token_and_keeps_the_refresh_token_out_of_reach(
    auth_env: AuthEnv,
) -> None:
    await auth_env.make_user("ana")
    async with auth_env.client() as browser:
        response = await auth_env.login(browser, "ana")
        assert response.status_code == 200
        body = response.json()
        assert body["token_type"] == "bearer" and body["expires_in"] == 15 * 60
        assert body["user"]["username"] == "itest-ana" and body["user"]["role"] == "admin"
        assert body["user"]["can_write"] is True
        assert "refresh" not in response.text  # the body never carries the refresh token

        cookie = response.headers["set-cookie"].lower()
        assert "refresh_token=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
        assert "path=/api/v1/auth" in cookie  # only sent to the auth endpoints

        me = await browser.get("/api/v1/auth/me", headers=_bearer(body["access_token"]))
        assert me.status_code == 200 and me.json()["username"] == "itest-ana"
        strategies = await browser.get("/api/v1/strategies", headers=_bearer(body["access_token"]))
        assert strategies.status_code == 200


async def test_protected_routes_reject_missing_garbage_and_tampered_tokens(
    auth_env: AuthEnv,
) -> None:
    await auth_env.make_user("bruno")
    async with auth_env.client() as browser:
        token = (await auth_env.login(browser, "bruno")).json()["access_token"]
        assert (await browser.get("/api/v1/strategies")).status_code == 401
        assert (
            await browser.get("/api/v1/strategies", headers=_bearer("garbage"))
        ).status_code == 401
        tampered = _bearer(token[:-3] + "abc")
        assert (await browser.get("/api/v1/strategies", headers=tampered)).status_code == 401
        assert (await browser.get("/api/v1/health/live")).status_code == 200  # probes stay open


async def test_wrong_password_and_unknown_user_are_indistinguishable(auth_env: AuthEnv) -> None:
    await auth_env.make_user("carla")
    async with auth_env.client() as browser:
        wrong = await auth_env.login(browser, "carla", "this is not the password")
        unknown = await auth_env.login(browser, "nobody-here")
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()
        assert wrong.headers["www-authenticate"] == "Bearer"


async def test_repeated_failures_lock_the_account_even_for_the_right_password(
    auth_env: AuthEnv,
) -> None:
    await auth_env.make_user("diego")
    async with auth_env.client() as browser:
        for _ in range(3):  # LOGIN_MAX_FAILURES
            assert (
                await auth_env.login(browser, "diego", "wrong password here")
            ).status_code == 401
        locked = await auth_env.login(browser, "diego")  # correct password, but locked
        assert locked.status_code == 401
        assert locked.json() == (await auth_env.login(browser, "nobody-here")).json()

        await auth_env.sql(  # time passes: the lock expires
            "UPDATE users SET locked_until = now() - interval '1 minute' "
            "WHERE username = 'itest-diego'"
        )
        assert (await auth_env.login(browser, "diego")).status_code == 200


async def test_refresh_rotates_the_cookie_and_a_replayed_token_kills_the_session(
    auth_env: AuthEnv,
) -> None:
    await auth_env.make_user("elisa")
    async with auth_env.client() as browser:
        login = await auth_env.login(browser, "elisa")
        first_cookie = browser.cookies["refresh_token"]

        refreshed = await browser.post("/api/v1/auth/refresh")
        assert refreshed.status_code == 200
        assert refreshed.json()["access_token"] != login.json()["access_token"]
        second_cookie = browser.cookies["refresh_token"]
        assert second_cookie != first_cookie  # rotated

        # An attacker (or a bug) replays the old, already-rotated token.
        thief = auth_env.client()
        thief.cookies.set("refresh_token", first_cookie, path="/api/v1/auth")
        async with thief:
            assert (await thief.post("/api/v1/auth/refresh")).status_code == 401

        # The reuse revoked the whole login: even the legitimate newest token is dead now.
        assert (await browser.post("/api/v1/auth/refresh")).status_code == 401
        events = {e["event_type"] for e in await _audit(auth_env)}
        assert "auth.refresh_reuse_detected" in events


async def _audit(env: AuthEnv) -> list[dict[str, Any]]:
    async with env.client() as client:
        response = await client.get("/api/v1/audit-events", headers=_bearer(SERVICE_TOKEN))
        return list(response.json())


async def test_logout_ends_the_session(auth_env: AuthEnv) -> None:
    await auth_env.make_user("fabio")
    async with auth_env.client() as browser:
        await auth_env.login(browser, "fabio")
        stale_cookie = browser.cookies["refresh_token"]
        assert (await browser.post("/api/v1/auth/logout")).status_code == 204
        assert "refresh_token" not in browser.cookies  # cleared

        replay = auth_env.client()
        replay.cookies.set("refresh_token", stale_cookie, path="/api/v1/auth")
        async with replay:
            assert (await replay.post("/api/v1/auth/refresh")).status_code == 401
        assert (await browser.post("/api/v1/auth/logout")).status_code == 204  # idempotent


async def test_changing_the_password_signs_out_every_session(auth_env: AuthEnv) -> None:
    await auth_env.make_user("gabi")
    async with auth_env.client() as laptop, auth_env.client() as phone:
        token = (await auth_env.login(laptop, "gabi")).json()["access_token"]
        await auth_env.login(phone, "gabi")
        headers = _bearer(token)

        wrong = {
            "current_password": "not my password",
            "new_password": "a brand new long passphrase",
        }
        assert (
            await laptop.post("/api/v1/auth/change-password", json=wrong, headers=headers)
        ).status_code == 401
        weak = {"current_password": PASSWORD, "new_password": "password1234"}
        assert (
            await laptop.post("/api/v1/auth/change-password", json=weak, headers=headers)
        ).status_code == 422

        good = {"current_password": PASSWORD, "new_password": "a brand new long passphrase"}
        assert (
            await laptop.post("/api/v1/auth/change-password", json=good, headers=headers)
        ).status_code == 204
        assert (await phone.post("/api/v1/auth/refresh")).status_code == 401  # signed out elsewhere
        assert (await auth_env.login(laptop, "gabi")).status_code == 401  # old password is dead
        assert (
            await auth_env.login(laptop, "gabi", "a brand new long passphrase")
        ).status_code == 200


async def test_viewers_read_but_only_admins_change_things(auth_env: AuthEnv) -> None:
    await auth_env.make_user("heitor", Role.VIEWER)
    await auth_env.make_user("irene", Role.ADMIN)
    async with auth_env.client() as viewer_browser, auth_env.client() as admin_browser:
        viewer = _bearer((await auth_env.login(viewer_browser, "heitor")).json()["access_token"])
        admin = _bearer((await auth_env.login(admin_browser, "irene")).json()["access_token"])

        assert (await viewer_browser.get("/api/v1/bots", headers=viewer)).status_code == 200
        assert (
            await viewer_browser.get("/api/v1/bots/overview", headers=viewer)
        ).status_code == 200
        body = {"name": "itest-role-bot", "strategy_type": "ema_crossover"}
        denied = await viewer_browser.post("/api/v1/bots", json=body, headers=viewer)
        assert denied.status_code == 403 and "admin" in denied.json()["detail"]
        kill = await viewer_browser.put(
            "/api/v1/system/kill-switch", json={"active": True}, headers=viewer
        )
        assert kill.status_code == 403
        assert (await viewer_browser.get("/api/v1/auth/users", headers=viewer)).status_code == 403

        # An admin passes the role check (this request then fails on its own validation).
        allowed = await admin_browser.post(
            "/api/v1/bots", json={**body, "strategy_type": "nope"}, headers=admin
        )
        assert allowed.status_code == 422
        assert (await admin_browser.get("/api/v1/auth/users", headers=admin)).status_code == 200


async def test_admins_manage_users_and_disabling_cuts_off_new_sessions(auth_env: AuthEnv) -> None:
    await auth_env.make_user("julia", Role.ADMIN)
    async with auth_env.client() as admin_browser, auth_env.client() as guest:
        admin = _bearer((await auth_env.login(admin_browser, "julia")).json()["access_token"])
        new_user = {"username": "itest-karen", "password": PASSWORD, "role": "viewer"}
        created = await admin_browser.post("/api/v1/auth/users", json=new_user, headers=admin)
        assert created.status_code == 201 and created.json()["role"] == "viewer"
        assert created.json()["can_write"] is False
        assert "password" not in created.text
        assert (
            await admin_browser.post("/api/v1/auth/users", json=new_user, headers=admin)
        ).status_code == 409
        weak = {**new_user, "username": "itest-leo", "password": "password1234"}
        assert (
            await admin_browser.post("/api/v1/auth/users", json=weak, headers=admin)
        ).status_code == 422

        assert (await auth_env.login(guest, "karen")).status_code == 200
        user_id = created.json()["id"]
        assert (
            await admin_browser.post(f"/api/v1/auth/users/{user_id}/disable", headers=admin)
        ).status_code == 200
        assert (await guest.post("/api/v1/auth/refresh")).status_code == 401  # session revoked
        assert (await auth_env.login(guest, "karen")).status_code == 401  # and no new logins

        me = (await admin_browser.get("/api/v1/auth/me", headers=admin)).json()
        own = await admin_browser.post(f"/api/v1/auth/users/{me['id']}/disable", headers=admin)
        assert own.status_code == 409  # an admin cannot lock themselves out


async def test_the_service_token_keeps_working_as_admin(auth_env: AuthEnv) -> None:
    async with auth_env.client() as client:
        headers = _bearer(SERVICE_TOKEN)
        assert (await client.get("/api/v1/bots", headers=headers)).status_code == 200
        write = await client.post(
            "/api/v1/bots", json={"name": "x", "strategy_type": "nope"}, headers=headers
        )
        assert write.status_code == 422  # allowed through (admin), rejected by validation
        me = (await client.get("/api/v1/auth/me", headers=headers)).json()
        assert (me["username"], me["role"]) == ("service", "admin")


async def test_cookie_endpoints_refuse_requests_from_foreign_sites(auth_env: AuthEnv) -> None:
    await auth_env.make_user("marta")
    async with auth_env.client() as browser:
        await auth_env.login(browser, "marta")
        evil = {"Origin": "https://evil.example"}
        assert (await browser.post("/api/v1/auth/refresh", headers=evil)).status_code == 403
        assert (await browser.post("/api/v1/auth/logout", headers=evil)).status_code == 403
        login = await browser.post(
            "/api/v1/auth/login",
            json={"username": "itest-marta", "password": PASSWORD},
            headers=evil,
        )
        assert login.status_code == 403
        assert (await browser.post("/api/v1/auth/refresh")).status_code == 200  # the real origin


async def test_cors_allows_the_frontend_origin_with_credentials(auth_env: AuthEnv) -> None:
    async with auth_env.client() as client:
        preflight = await client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type,authorization",
            },
        )
        assert preflight.headers["access-control-allow-origin"] == ORIGIN
        assert preflight.headers["access-control-allow-credentials"] == "true"
