import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    SessionManager,
    get_session_id,
    validate_csrf,
)
from app.db.models.admin_user import AdminUser
from app.db.session import get_db
from app.services.admin_service import get_admin_by_id
from app.services.rate_limiter import RateLimiter


async def get_valkey(request: Request) -> Redis:
    return request.app.state.valkey


async def get_session_manager(valkey: Redis = Depends(get_valkey)) -> SessionManager:
    return SessionManager(valkey)


@dataclass
class CurrentAdmin:
    admin: AdminUser
    session_id: str
    session_data: dict


async def get_current_admin(
    request: Request,
    session: AsyncSession = Depends(get_db),
    session_manager: SessionManager = Depends(get_session_manager),
) -> CurrentAdmin:
    sid = get_session_id(request)
    if not sid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    session_data = await session_manager.get_session(sid)
    if not session_data:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    validate_csrf(request, session_data)

    admin_id = uuid.UUID(session_data["admin_user_id"])
    admin = await get_admin_by_id(session, admin_id)
    if not admin or not admin.is_active:
        await session_manager.delete_session(sid, str(admin_id) if admin else "")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access revoked")

    rate_limiter = RateLimiter(request.app.state.valkey)
    await rate_limiter.enforce(f"api:{admin_id}", settings.rate_limit_api_per_minute)

    await session_manager.refresh_session(sid, session_data)
    return CurrentAdmin(admin=admin, session_id=sid, session_data=session_data)


def get_client_meta(request: Request) -> tuple[str | None, str | None]:
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return ip, ua
