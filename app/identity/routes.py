from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy.orm import Session

from app.identity.model import Credentials, Me, User, UserORM
from app.identity.service import SESSION_TTL, authenticate, login, logout, register
from app.REST.data.database import get_db

COOKIE = "auth_token"
router = APIRouter(prefix="/auth", tags=["identity"])


def _set_cookie(response: Response, token: str) -> None:
    # HttpOnly: JS cannot read it; SameSite=Lax: not sent on cross-site POSTs (CSRF)
    response.set_cookie(
        COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), httponly=True, samesite="lax", path="/"
    )


def current_session(response: Response, auth_token: str | None = Cookie(None), db: Session = Depends(get_db)):
    user, session = authenticate(db, auth_token)
    _set_cookie(response, auth_token)  # extended session -> extended cookie
    return user, session


def current_user(auth=Depends(current_session)) -> UserORM:
    """Dependency for other modules (cart): 401 without a valid session."""
    return auth[0]


@router.post("/register", response_model=User, status_code=201)
def post_register(credentials: Credentials, db: Session = Depends(get_db)):
    return register(db, credentials)


@router.post("/login", response_model=User)
def post_login(credentials: Credentials, response: Response, db: Session = Depends(get_db)):
    token = login(db, credentials)
    _set_cookie(response, token)
    user, _ = authenticate(db, token)
    return user


@router.get("/me", response_model=Me)
def get_me(auth=Depends(current_session)):
    user, session = auth
    return Me(id=user.id, email=user.email, created_at=user.created_at, session_expires_at=session.expires_at)


@router.post("/logout", status_code=204)
def post_logout(response: Response, auth_token: str | None = Cookie(None), db: Session = Depends(get_db)):
    logout(db, auth_token)
    response.delete_cookie(COOKIE, path="/")
    response.status_code = 204
    return response
