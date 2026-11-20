from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.REST.data.database import get_db
from app.REST.model.notification_orm import Status
from app.REST.model.notification_schema import Notification, NotificationCreate, ProcessReadyResult
from app.REST.service.notification_service import (
    cancel_notification,
    create_notification,
    get_notification,
    list_notifications,
    process_ready,
    send_now,
)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


def _found(n):
    if n is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return n


@router.get("", response_model=list[Notification])
def get_notifications(status: Status | None = None, db: Session = Depends(get_db)):
    return list_notifications(db, status)


@router.post(
    "",
    response_model=Notification,
    status_code=201,
    responses={200: {"description": "Same idempotency_key already used: the original is returned"}},
)
def post_notification(payload: NotificationCreate, response: Response, db: Session = Depends(get_db)):
    n, created = create_notification(db, payload)
    if not created:
        response.status_code = 200
    return n


# Declared before /{id} routes so "process-ready" is never parsed as an id
@router.post("/process-ready", response_model=ProcessReadyResult)
def post_process_ready(db: Session = Depends(get_db)):
    return process_ready(db)


@router.get("/{id}", response_model=Notification)
def get_notification_endpoint(id: int, db: Session = Depends(get_db)):
    return _found(get_notification(db, id))


@router.post("/{id}/send-now", response_model=Notification)
def post_send_now(id: int, db: Session = Depends(get_db)):
    return _found(send_now(db, id))


@router.post("/{id}/cancel", response_model=Notification)
def post_cancel(id: int, db: Session = Depends(get_db)):
    return _found(cancel_notification(db, id))
