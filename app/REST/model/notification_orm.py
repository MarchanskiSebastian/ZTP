from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.REST.data.database import Base


class Channel(str, Enum):
    EMAIL = "EMAIL"
    PUSH = "PUSH"


class Status(str, Enum):
    PENDING = "PENDING"      # Oczekujące
    SENT = "SENT"            # Wysłane
    FAILED = "FAILED"        # Nieudane
    CANCELLED = "CANCELLED"  # Anulowane


# State machine: only PENDING can move; SENT / FAILED / CANCELLED are terminal
TRANSITIONS: dict[Status, set[Status]] = {
    Status.PENDING: {Status.SENT, Status.FAILED, Status.CANCELLED},
    Status.SENT: set(),
    Status.FAILED: set(),
    Status.CANCELLED: set(),
}


class NotificationORM(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    channel: Mapped[str] = mapped_column(String, nullable=False)
    recipient: Mapped[str] = mapped_column(String, nullable=False)
    subject: Mapped[str] = mapped_column(String, nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default=Status.PENDING.value)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String, unique=True)
