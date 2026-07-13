import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qsl

from fastapi import HTTPException, Request, Response, status
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.admin_user import AdminUser
from starlette.status import HTTP_403_FORBIDDEN

SESSION_COOKIE = "session"
CSRF_COOKIE = "csrf_token"


def _build_data_check_string(data: dict[str, str]) -> str:
    pairs = sorted((k, v) for k, v in data.items() if k != "hash")
    return "\n".join(f"{k}={v}" for k, v in pairs)

def validate_telegram_init_data(init_data: str, bot_token: str) -> dict[str, Any]:
    parsed = dict[str, str](parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing hash")

    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    data_check_string = _build_data_check_string(parsed)
    calculated_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, calculated_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid initData")

    auth_date = int(parsed.get("auth_date", 0))
    now = int(datetime.now(UTC).timestamp())
    if now - auth_date > settings.auth_date_max_age_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="initData expired")

    user_raw = parsed.get("user")
    if not user_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing user")
    user = json.loads(user_raw)
    return user

async def get_admin_by_telegram_id(session: AsyncSession, telegram_user_id: int) -> AdminUser:
    result = await session.execute(
        select(AdminUser).where(
            AdminUser.telegram_user_id == telegram_user_id,
            AdminUser.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


class SessionManager:
    def __init__(self, valkey: Redis):
        self.valkey = valkey

    def _session_key(self, sid: str) -> str:
        return f"session:{sid}"

    def _admin_sessions_key(self, admin_user_id: str) -> str:
        return f"admin_sessions:{admin_user_id}"

    async def create_session(self, admin_user_id: int) -> tuple[str, str, str]:
        sid = str(uuid.uuid4())
        csrf_token = secrets.token_urlsafe(32)
        now = datetime.now(UTC)
        payload = {
            "admin_user_id": admin_user_id,
            "created_at": now.isoformat(),
            "last_seen": now.isoformat(),
            "csrf_token": csrf_token,
        }
        ttl = settings.session_ttl_minutes * 60
        pipe = self.valkey.pipeline()
        pipe.set(self._session_key(sid), json.dumps(payload), ex=ttl)
        pipe.sadd(self._admin_sessions_key(admin_user_id), sid)
        await pipe.execute()
        return sid, csrf_token, csrf_token

    async def get_session(self, sid: str) -> dict[str, Any] | None:
        raw = await self.valkey.get(self._session_key(sid))
        if not raw:
            return None
        return json.loads(raw)

    async def refresh_session(self, sid: str, data: dict[str, Any]) -> None:
        data["last_seen"] = datetime.now(UTC).isoformat()
        created = datetime.fromisoformat(data["created_at"])
        absolute_expiry = created + timedelta(hours=settings.session_absolute_ttl_hours)
        if datetime.now(UTC) >= absolute_expiry:
            await self.delete_session(sid, data.get("admin_user_id", ""))
            return
        ttl = settings.session_ttl_minutes * 60
        await self.valkey.set(self._session_key(sid), json.dumps(data), ex=ttl)

    async def delete_session(self, sid: str, admin_user_id: str) -> None:
        pipe = self.valkey.pipeline()
        pipe.delete(self._session_key(sid))
        if admin_user_id:
            pipe.srem(self._admin_sessions_key(admin_user_id), sid)
        await pipe.execute()

    async def invalidate_all_sessions(self, admin_user_id: str) -> None:
        key = self._admin_sessions_key(admin_user_id)
        sids = await self.valkey.smembers(key)
        if not sids:
            return
        pipe = self.valkey.pipeline()
        for sid in sids:
            sid_str = sid.decode() if isinstance(sid, bytes) else sid
            pipe.delete(self._session_key(sid_str))
        pipe.delete(key)
        await pipe.execute()


def set_session_cookies(response: Response, sid: str, csrf_token: str) -> None:
    secure = not settings.cors_origins.startswith("http://localhost")
    max_age = settings.session_ttl_minutes * 60
    response.set_cookie(
        SESSION_COOKIE,
        sid,
        httponly=True,
        secure=secure,
        samesite="none" if secure else "lax",
        max_age=max_age,
        path="/",
    )
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        httponly=False,
        secure=secure,
        samesite="none" if secure else "lax",
        max_age=max_age,
        path="/",
    )


def clear_session_cookies(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(CSRF_COOKIE, path="/")


def get_session_id(request: Request) -> str:
    return request.cookies.get(SESSION_COOKIE)


def validate_csrf(request: Request, session_data: dict[str, Any]) -> None:
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    header_token = request.headers.get(settings.csrf_header_name)
    cookie_token = request.cookies.get(CSRF_COOKIE)
    session_token = session_data.get("csrf_token")
    if not header_token or not cookie_token:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing")
    if not hmac.compare_digest(header_token, cookie_token):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="CSRF token mismatch")
    if not hmac.compare_digest(header_token, session_token):
        raise HTTPException(status_code=HTTP_403_FORBIDDEN, detail="CSRF session mismatch")
