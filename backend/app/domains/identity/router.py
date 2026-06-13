from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.database import get_session

from .models import User
from .schemas import AuthSessionResponse, AuthStatusResponse, LoginRequest, RegisterRequest
from .service import AuthenticationError, ConflictError, IdentityService, user_response

SESSION_COOKIE = "session"

router = APIRouter(prefix="/auth", tags=["auth"])


def set_session_cookie(response: Response, raw_token: str, *, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        raw_token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=14 * 24 * 60 * 60,
        path="/",
    )


def clear_session_cookie(response: Response, *, secure: bool) -> None:
    response.delete_cookie(
        SESSION_COOKIE,
        path="/",
        secure=secure,
        httponly=True,
        samesite="lax",
    )


async def require_user(
    session: Annotated[AsyncSession, Depends(get_session)],
    raw_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> User:
    user = await IdentityService(session).authenticate_token(raw_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    return user


@router.post("/register", response_model=AuthSessionResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> AuthSessionResponse:
    service = IdentityService(session)
    try:
        user, raw_token = await service.register(
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            organization_name=body.organization_name,
            user_agent=user_agent,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    set_session_cookie(response, raw_token, secure=settings.is_production)
    return AuthSessionResponse(
        user=user_response(user),
        organizations=await service.organizations_for_user(user.id),
    )


@router.post("/login", response_model=AuthSessionResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user_agent: Annotated[str | None, Header(alias="User-Agent")] = None,
) -> AuthSessionResponse:
    service = IdentityService(session)
    try:
        user, raw_token = await service.login(
            email=body.email,
            password=body.password,
            user_agent=user_agent,
        )
    except (ValueError, AuthenticationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码不正确",
        ) from exc
    set_session_cookie(response, raw_token, secure=settings.is_production)
    return AuthSessionResponse(
        user=user_response(user),
        organizations=await service.organizations_for_user(user.id),
    )


@router.post("/logout", response_model=AuthStatusResponse)
async def logout(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    raw_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE)] = None,
) -> AuthStatusResponse:
    await IdentityService(session).logout(raw_token)
    clear_session_cookie(response, secure=settings.is_production)
    return AuthStatusResponse(status="logged_out")


@router.get("/me", response_model=AuthSessionResponse)
async def me(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(require_user)],
) -> AuthSessionResponse:
    return AuthSessionResponse(
        user=user_response(user),
        organizations=await IdentityService(session).organizations_for_user(user.id),
    )
