from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field, SecretStr

from core.config import Settings
from core.security.auth import Principal, require_admin, require_auth
from modules.auth.domain import InvalidCredentials, Role, User
from modules.auth.service import AuthService, IssuedSession

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "refresh_token"
_COOKIE_PATH = "/api/v1/auth"  # the browser only sends the cookie to these endpoints


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: SecretStr = Field(min_length=1, max_length=256)


class UserOut(BaseModel):
    id: UUID
    username: str
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class TokenOut(BaseModel):
    """Keep ``access_token`` in memory and send it as ``Authorization: Bearer``. The refresh
    token travels only in an httpOnly cookie, out of reach of page scripts."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access token lifetime, seconds")
    user: UserOut


class ChangePasswordIn(BaseModel):
    current_password: SecretStr
    new_password: SecretStr = Field(min_length=12, max_length=256)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    password: SecretStr = Field(min_length=12, max_length=256)
    role: Role = Role.VIEWER


def _service(request: Request) -> AuthService:
    service: AuthService = request.app.state.container.auth
    return service


def _settings(request: Request) -> Settings:
    settings: Settings = request.app.state.container.settings
    return settings


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _check_origin(request: Request) -> None:
    """Cookie endpoints: a browser request from a foreign site is refused (CSRF defence in
    depth on top of SameSite=Lax)."""
    origin = request.headers.get("origin")
    if origin is not None and origin not in _settings(request).cors_origins:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "origin not allowed")


def _set_cookie(request: Request, response: Response, session: IssuedSession) -> None:
    settings = _settings(request)
    response.set_cookie(
        REFRESH_COOKIE,
        session.refresh_token,
        max_age=int(settings.refresh_token_days * 86400),
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        path=_COOKIE_PATH,
    )


def _token_out(session: IssuedSession) -> TokenOut:
    return TokenOut(
        access_token=session.access_token,
        expires_in=session.expires_in,
        user=_user_out(session.user),
    )


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, request: Request, response: Response) -> TokenOut:
    """Sign in. Returns the access token and sets the refresh-token cookie."""
    _check_origin(request)
    session = await _service(request).login(
        body.username, body.password.get_secret_value(), request.headers.get("user-agent")
    )
    _set_cookie(request, response, session)
    return _token_out(session)


@router.post("/refresh", response_model=TokenOut)
async def refresh(request: Request, response: Response) -> TokenOut:
    """Trade the refresh cookie for a new access token (the cookie is rotated)."""
    _check_origin(request)
    raw = request.cookies.get(REFRESH_COOKIE)
    if not raw:
        raise InvalidCredentials("no session")
    session = await _service(request).refresh(raw, request.headers.get("user-agent"))
    _set_cookie(request, response, session)
    return _token_out(session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response) -> None:
    """End this login: revokes the refresh token and clears the cookie."""
    _check_origin(request)
    await _service(request).logout(request.cookies.get(REFRESH_COOKIE))
    response.delete_cookie(REFRESH_COOKIE, path=_COOKIE_PATH)


@router.get("/me", response_model=UserOut)
async def me(request: Request, principal: Principal = Depends(require_auth)) -> Any:
    """The signed-in user (the frontend uses this to know the role)."""
    if principal.kind != "user":
        return UserOut(
            id=UUID(int=0),
            username=principal.username,
            role=Role(principal.role),
            is_active=True,
            created_at=datetime.min,
            last_login_at=None,
        )
    return _user_out(await _service(request).get_user(UUID(principal.subject)))


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordIn,
    request: Request,
    response: Response,
    principal: Principal = Depends(require_auth),
) -> None:
    """Change your password; every session (including this one) is signed out."""
    if principal.kind != "user":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "only signed-in users have a password")
    await _service(request).change_password(
        UUID(principal.subject),
        body.current_password.get_secret_value(),
        body.new_password.get_secret_value(),
    )
    response.delete_cookie(REFRESH_COOKIE, path=_COOKIE_PATH)


@router.post(
    "/users",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_user(
    body: UserCreate, request: Request, principal: Principal = Depends(require_auth)
) -> UserOut:
    """Create a user (admin only). Give a collaborator `viewer` for read-only access."""
    user = await _service(request).create_user(
        body.username, body.password.get_secret_value(), body.role, actor=principal.username
    )
    return _user_out(user)


@router.get("/users", response_model=list[UserOut], dependencies=[Depends(require_admin)])
async def list_users(request: Request) -> list[UserOut]:
    return [_user_out(u) for u in await _service(request).list_users()]


@router.post(
    "/users/{user_id}/disable",
    response_model=UserOut,
    dependencies=[Depends(require_admin)],
)
async def disable_user(
    user_id: UUID, request: Request, principal: Principal = Depends(require_auth)
) -> UserOut:
    """Disable a user and sign them out everywhere. You cannot disable yourself."""
    if principal.subject == str(user_id):
        raise HTTPException(status.HTTP_409_CONFLICT, "you cannot disable your own account")
    return _user_out(await _service(request).set_active(user_id, False, principal.username))


@router.post(
    "/users/{user_id}/enable",
    response_model=UserOut,
    dependencies=[Depends(require_admin)],
)
async def enable_user(
    user_id: UUID, request: Request, principal: Principal = Depends(require_auth)
) -> UserOut:
    return _user_out(await _service(request).set_active(user_id, True, principal.username))
