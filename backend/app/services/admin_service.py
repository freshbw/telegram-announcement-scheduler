import logging
import uuid
from datetime import datetime, UTC

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.admin_user import AdminUser

logger = logging.getLogger(__name__)


def bootstrap_admins_sync(connection: Connection, telegram_ids: list[int]) -> int:
    count = connection.execute(
        select(func.count()).select_from(AdminUser.__table__)
    ).scalar_one()
    if count > 0:
        return 0
    if not telegram_ids:
        logger.warning("admin_users empty and INITIAL_ADMIN_TELEGRAM_IDS not set")
        return 0
    for tid in telegram_ids:
        connection.execute(
            AdminUser.__table__.insert().values(
                id=uuid.uuid4(),
                telegram_user_id=tid,
                is_active=True,
                created_by_id=None,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        )
    logger.info("Bootstrapped %d admin(s) from env", len(telegram_ids))
    return len(telegram_ids)


async def bootstrap_admins(session: AsyncSession, telegram_ids: list[int]) -> int:
    count = await session.scalar(select(func.count()).select_from(AdminUser))
    if count and count > 0:
        return 0
    if not telegram_ids:
        logger.warning("admin_users empty and INITIAL_ADMIN_TELEGRAM_IDS not set")
        return 0
    for tid in telegram_ids:
        session.add(AdminUser(telegram_user_id=tid, is_active=True, created_by_id=None))
    await session.commit()
    logger.info("Bootstrapped %d admin(s) from env", len(telegram_ids))
    return len(telegram_ids)


async def get_admin_by_id(session: AsyncSession, admin_id: uuid.UUID) -> AdminUser | None:
    result = await session.execute(select(AdminUser).where(AdminUser.id == admin_id))
    return result.scalar_one_or_none()
