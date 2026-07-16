from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db, get_session_manager, get_valkey
from app.core.config import settings
from app.core.security import (
    get_admin_by_telegram_id,
    set_session_cookies,
    validate_telegram_init_data,
)
from app.schemas.api import AuthMeResponse, TelegramAuthRequest
from app.services.rate_limiter import RateLimiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/telegram")
async def login_telegram(
    body: TelegramAuthRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db),
    valkey=Depends(get_valkey),
    session_manager=Depends(get_session_manager),
):
    ip = request.client.host if request.client else "unknown"
    rate_limiter = RateLimiter(valkey)
    await rate_limiter.enforce(f"auth:{ip}", settings.rate_limit_auth_per_minute)

    if not settings.bot_token:
        raise HTTPException(status_code=500, detail="Bot token not set")

    user = validate_telegram_init_data(body.init_data, settings.bot_token)
    telegram_id = int(user["id"])

    admin = await get_admin_by_telegram_id(session, telegram_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    admin.username = user.get("username")
    first = user.get("first_name", "")
    last = user.get("last_name", "")
    admin.display_name = f"{first} {last}".strip() or admin.display_name
    admin.last_login_at = datetime.now(UTC)
    await session.commit()

    sid, csrf_token, _ = await session_manager.create_session(str(admin.id))
    set_session_cookies(response, sid, csrf_token)
    return {"ok": True, "csrf_token": csrf_token}


@router.get("/me", response_model=AuthMeResponse)
async def me(current=Depends(get_current_admin)):
    return AuthMeResponse(
        admin=current.admin,
        csrf_token=current.session_data.get("csrf_token", ""),
    )
