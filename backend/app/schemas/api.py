import uuid
from datetime import datetime

from pydantic import BaseModel


class AdminUserOut(BaseModel):
    id: uuid.UUID
    telegram_user_id: int
    username: str | None
    display_name: str | None
    is_active: bool
    created_by_id: uuid.UUID | None
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TelegramAuthRequest(BaseModel):
    init_data: str


class AuthMeResponse(BaseModel):
    admin: AdminUserOut
    csrf_token: str
