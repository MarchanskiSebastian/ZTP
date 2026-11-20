from datetime import datetime, timezone

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator

from app.REST.model.notification_orm import Channel, Status


class NotificationCreate(BaseModel):
    channel: Channel
    recipient: str = Field(min_length=1, max_length=255, description="EMAIL: address, PUSH: ntfy topic")
    subject: str = Field("", max_length=255)
    message: str = Field(min_length=1)
    # AwareDatetime rejects times without a zone (422); stored and returned in UTC
    scheduled_at: AwareDatetime | None = Field(None, description="ISO 8601 with offset, default: now")
    idempotency_key: str | None = Field(None, min_length=1, max_length=100)

    @field_validator("scheduled_at")
    @classmethod
    def to_utc(cls, value: datetime | None) -> datetime | None:
        return value.astimezone(timezone.utc) if value else value


class Notification(BaseModel):
    id: int
    channel: Channel
    recipient: str
    subject: str
    message: str
    status: Status
    scheduled_at: datetime
    created_at: datetime
    updated_at: datetime
    sent_at: datetime | None
    attempts: int
    last_error: str | None
    idempotency_key: str | None

    model_config = ConfigDict(from_attributes=True)


class ProcessReadyResult(BaseModel):
    processed: int
    sent: int
    failed: int
