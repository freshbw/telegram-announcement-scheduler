import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, new_uuid


class ScheduleStatus(StrEnum):
    draft = "draft"
    active = "active"
    paused = "paused"
    exhausted = "exhausted"
    failed = "failed"
    archived = "archived"


class ScheduleMode(StrEnum):
    interval = "interval"
    daily = "daily"


class MediaType(StrEnum):
    photo = "photo"
    video = "video"
    document = "document"


class ScheduledMessage(Base, TimestampMixin):
    __tablename__ = "scheduled_messages"
    __table_args__ = (
        CheckConstraint("credits_remaining >= 0", name="ck_credits_remaining_nonneg"),
        Index(
            "ix_scheduled_message_active_next_run",
            "status",
            "next_run_at",
            postgresql_where="status = 'active'",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=new_uuid)
    channel_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("channels.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[ScheduleStatus] = mapped_column(
        Enum(ScheduleStatus, name="schedule_status"), default=ScheduleStatus.draft, nullable=False
    )
    mode: Mapped[ScheduleMode] = mapped_column(
        Enum(ScheduleMode, name="schedule_mode"), nullable=False
    )
    schedule_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    content_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    media_type: Mapped[MediaType | None] = mapped_column(
        Enum(MediaType, name="media_type"), nullable=True
    )
    media_file_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    credits_total: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    credits_remaining: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    send_immediately: Mapped[bool] = mapped_column(default=True, nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=False
    )

    channel = relationship("Channel")
    created_by = relationship("AdminUser")
