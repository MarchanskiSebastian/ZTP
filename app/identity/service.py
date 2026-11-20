import hashlib
import hmac
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.identity.model import Credentials, UserORM, UserSessionORM
from app.identity.repository import (
    add_session,
    add_user,
    delete_session,
    delete_sessions_of_user,
    get_session_by_token_hash,
    get_user_by_email,
    get_user_by_id,
)
from app.REST.data.product_repository import commit
from app.REST.service.product_validators import ConflictError, UnauthorizedError, ValidationError

# OWASP 2023 recommendation for PBKDF2-HMAC-SHA256; stored per user so it can be raised later
PBKDF2_ITERATIONS = int(os.getenv("PBKDF2_ITERATIONS", "600000"))
SESSION_TTL = timedelta(minutes=int(os.getenv("SESSION_TTL_MINUTES", "30")))

_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations).hex()


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def validate_credentials(c: Credentials) -> None:
    if not _EMAIL.fullmatch(c.email):
        raise ValidationError("Niepoprawny adres e-mail.")
    if len(c.password) < 8 or not re.search(r"[A-Za-z]", c.password) or not re.search(r"\d", c.password):
        raise ValidationError("Hasło musi mieć min. 8 znaków, w tym literę i cyfrę.")


def register(db: Session, c: Credentials) -> UserORM:
    validate_credentials(c)
    if get_user_by_email(db, c.email) is not None:
        raise ConflictError("Użytkownik o takim adresie e-mail już istnieje.")
    salt = secrets.token_bytes(16)
    user = add_user(
        db,
        UserORM(
            email=c.email.lower(),
            password_hash=hash_password(c.password, salt, PBKDF2_ITERATIONS),
            password_salt=salt.hex(),
            password_iterations=PBKDF2_ITERATIONS,
        ),
    )
    commit(db)
    return user


def login(db: Session, c: Credentials) -> str:
    """Returns the raw session token for the cookie. The previous session of the user is replaced."""
    user = get_user_by_email(db, c.email)
    if user is None or not hmac.compare_digest(
        user.password_hash,
        hash_password(c.password, bytes.fromhex(user.password_salt), user.password_iterations),
    ):
        raise UnauthorizedError("Nieprawidłowy e-mail lub hasło.")  # same message: no user enumeration
    token = secrets.token_urlsafe(32)
    delete_sessions_of_user(db, user.id)  # overwrite: only one active session per user
    add_session(db, UserSessionORM(user_id=user.id, token_hash=_token_hash(token), expires_at=_now() + SESSION_TTL))
    commit(db)
    return token


def authenticate(db: Session, token: str | None) -> tuple[UserORM, UserSessionORM]:
    """Valid session -> its user; every authenticated request extends the session (sliding expiration)."""
    session = get_session_by_token_hash(db, _token_hash(token)) if token else None
    if session is None:
        raise UnauthorizedError("Brak aktywnej sesji. Zaloguj się.")
    now = _now()
    if session.expires_at <= now:
        delete_session(db, session)
        commit(db)
        raise UnauthorizedError("Sesja wygasła. Zaloguj się ponownie.")
    session.last_seen_at = now
    session.expires_at = now + SESSION_TTL
    commit(db)
    return get_user_by_id(db, session.user_id), session


def logout(db: Session, token: str | None) -> None:
    session = get_session_by_token_hash(db, _token_hash(token)) if token else None
    if session is not None:
        delete_session(db, session)
        commit(db)
