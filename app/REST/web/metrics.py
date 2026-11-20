from fastapi import APIRouter, Depends
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.REST.data.database import get_db
from app.REST.data.notification_repository import count_by_status_and_channel
from app.REST.model.notification_orm import Channel, Status
from app.REST.service.notification_service import DELIVERIES

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_class=PlainTextResponse, include_in_schema=False)
def metrics(db: Session = Depends(get_db)):
    """Prometheus text exposition format (version 0.0.4)."""
    counts = {(s, c): n for s, c, n in count_by_status_and_channel(db)}
    lines = [
        "# HELP notifications_current Notifications in the database by status and channel.",
        "# TYPE notifications_current gauge",
    ]
    # every combination is emitted (also 0) so Prometheus series never disappear
    for s in Status:
        for c in Channel:
            lines.append(f'notifications_current{{status="{s.value}",channel="{c.value}"}} {counts.get((s.value, c.value), 0)}')
    lines += [
        "# HELP notification_deliveries_total Delivery attempts since app start.",
        "# TYPE notification_deliveries_total counter",
    ]
    for c in Channel:
        for result in ("sent", "failed"):
            lines.append(f'notification_deliveries_total{{channel="{c.value}",result="{result}"}} {DELIVERIES[(c.value, result)]}')
    return PlainTextResponse("\n".join(lines) + "\n", media_type="text/plain; version=0.0.4")
