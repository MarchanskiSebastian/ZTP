from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.REST.model.notification_orm import NotificationORM, Status


def get_all_notifications(db: Session, status: Status | None = None) -> list[NotificationORM]:
    query = select(NotificationORM).order_by(NotificationORM.id)
    if status is not None:
        query = query.where(NotificationORM.status == status.value)
    return list(db.execute(query).scalars().all())


def get_notification_by_id(db: Session, notification_id: int, lock: bool = False) -> NotificationORM | None:
    query = select(NotificationORM).where(NotificationORM.id == notification_id)
    if lock:
        query = query.with_for_update()
    return db.execute(query).scalar_one_or_none()


def get_notification_by_idempotency_key(db: Session, key: str) -> NotificationORM | None:
    query = select(NotificationORM).where(NotificationORM.idempotency_key == key)
    return db.execute(query).scalar_one_or_none()


def lock_ready_notifications(db: Session, now: datetime, limit: int) -> list[NotificationORM]:
    # SKIP LOCKED: the worker and process-ready can run at once without sending twice
    query = (
        select(NotificationORM)
        .where(NotificationORM.status == Status.PENDING.value, NotificationORM.scheduled_at <= now)
        .order_by(NotificationORM.scheduled_at, NotificationORM.id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    return list(db.execute(query).scalars().all())


def count_by_status_and_channel(db: Session) -> list[tuple[str, str, int]]:
    query = select(NotificationORM.status, NotificationORM.channel, func.count()).group_by(
        NotificationORM.status, NotificationORM.channel
    )
    return [tuple(row) for row in db.execute(query).all()]


def add_notification(db: Session, notification: NotificationORM) -> NotificationORM:
    db.add(notification)
    db.flush()
    db.refresh(notification)
    return notification


def save_notification(db: Session, notification: NotificationORM) -> NotificationORM:
    db.flush()
    db.refresh(notification)
    return notification
