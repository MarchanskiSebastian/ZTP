import re
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.REST.data.notification_repository import (
    add_notification,
    get_all_notifications,
    get_notification_by_id,
    get_notification_by_idempotency_key,
    lock_ready_notifications,
    save_notification,
)
from app.REST.data.product_repository import commit
from app.REST.model.notification_orm import TRANSITIONS, Channel, NotificationORM, Status
from app.REST.model.notification_schema import NotificationCreate
from app.REST.service import delivery
from app.REST.service.product_validators import ConflictError, ValidationError

# Delivery attempts since process start, exposed by /metrics: (channel, result) -> count
DELIVERIES: Counter[tuple[str, str]] = Counter()

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
_NTFY_TOPIC = re.compile(r"[-_A-Za-z0-9]{1,64}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def change_status(n: NotificationORM, new: Status) -> None:
    current = Status(n.status)
    if new not in TRANSITIONS[current]:
        raise ConflictError(f"Niedozwolona zmiana statusu: {current.value} -> {new.value}.")
    n.status = new.value


def _validate_recipient(payload: NotificationCreate) -> None:
    if payload.channel == Channel.EMAIL and not _EMAIL.fullmatch(payload.recipient):
        raise ValidationError("Dla kanału EMAIL odbiorca musi być poprawnym adresem e-mail.")
    if payload.channel == Channel.PUSH and not _NTFY_TOPIC.fullmatch(payload.recipient):
        raise ValidationError("Dla kanału PUSH odbiorca musi być tematem ntfy (litery, cyfry, - i _, max 64).")


def _deliver(n: NotificationORM) -> bool:
    n.attempts += 1
    try:
        delivery.dispatch(n)
    except Exception as exc:  # any channel error = failed delivery, never crash the caller
        change_status(n, Status.FAILED)
        n.last_error = str(exc)[:500] or exc.__class__.__name__
        DELIVERIES[(n.channel, "failed")] += 1
        return False
    change_status(n, Status.SENT)
    n.sent_at = _now()
    n.last_error = None
    DELIVERIES[(n.channel, "sent")] += 1
    return True


def list_notifications(db: Session, status: Status | None = None) -> list[NotificationORM]:
    return get_all_notifications(db, status)


def get_notification(db: Session, notification_id: int) -> NotificationORM | None:
    return get_notification_by_id(db, notification_id)


def create_notification(db: Session, payload: NotificationCreate) -> tuple[NotificationORM, bool]:
    """Returns (notification, created). A repeated idempotency_key returns the original."""
    if payload.idempotency_key:
        existing = get_notification_by_idempotency_key(db, payload.idempotency_key)
        if existing is not None:
            return existing, False
    _validate_recipient(payload)
    n = add_notification(
        db,
        NotificationORM(
            channel=payload.channel.value,
            recipient=payload.recipient,
            subject=payload.subject,
            message=payload.message,
            status=Status.PENDING.value,
            scheduled_at=payload.scheduled_at or _now(),
            idempotency_key=payload.idempotency_key,
        ),
    )
    commit(db)
    return n, True


def cancel_notification(db: Session, notification_id: int) -> NotificationORM | None:
    n = get_notification_by_id(db, notification_id, lock=True)
    if n is None:
        return None
    change_status(n, Status.CANCELLED)
    n = save_notification(db, n)
    commit(db)
    return n


def send_now(db: Session, notification_id: int) -> NotificationORM | None:
    """Deliver one PENDING notification immediately, ignoring scheduled_at."""
    n = get_notification_by_id(db, notification_id, lock=True)
    if n is None:
        return None
    if n.status != Status.PENDING.value:
        raise ConflictError(f"Można wysłać tylko powiadomienie PENDING (aktualnie {n.status}).")
    _deliver(n)
    n = save_notification(db, n)
    commit(db)
    return n


def process_ready(db: Session, limit: int = 100) -> dict[str, int]:
    """Deliver every PENDING notification whose scheduled_at has passed (UTC)."""
    ready = lock_ready_notifications(db, _now(), limit)
    sent = sum(_deliver(n) for n in ready)
    db.flush()
    commit(db)
    return {"processed": len(ready), "sent": sent, "failed": len(ready) - sent}
