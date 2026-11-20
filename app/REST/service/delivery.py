import base64
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

from app.REST.model.notification_orm import Channel, NotificationORM

MAILHOG_HOST = os.getenv("MAILHOG_HOST", "localhost")
MAILHOG_PORT = int(os.getenv("MAILHOG_PORT", "1025"))
MAIL_FROM = os.getenv("MAIL_FROM", "noreply@ztp.local")
NTFY_URL = os.getenv("NTFY_URL", "http://localhost:8080")
TIMEOUT = 5


def send_email(n: NotificationORM) -> None:
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = n.recipient
    msg["Subject"] = n.subject
    msg.set_content(n.message)
    with smtplib.SMTP(MAILHOG_HOST, MAILHOG_PORT, timeout=TIMEOUT) as smtp:
        smtp.send_message(msg)


def send_push(n: NotificationORM) -> None:
    request = urllib.request.Request(
        f"{NTFY_URL}/{urllib.parse.quote(n.recipient, safe='')}",
        data=n.message.encode(),
        # HTTP headers are latin-1; ntfy decodes RFC 2047 encoded titles
        headers={"Title": f"=?UTF-8?B?{base64.b64encode(n.subject.encode()).decode()}?="},
        method="POST",
    )
    urllib.request.urlopen(request, timeout=TIMEOUT).close()  # raises on non-2xx


SENDERS = {Channel.EMAIL.value: send_email, Channel.PUSH.value: send_push}


def dispatch(n: NotificationORM) -> None:
    """Pick the delivery channel; any exception means the delivery failed."""
    SENDERS[n.channel](n)
