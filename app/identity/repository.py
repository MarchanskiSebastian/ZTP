from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.identity.model import UserORM, UserSessionORM


def get_user_by_email(db: Session, email: str) -> UserORM | None:
    return db.execute(select(UserORM).where(func.lower(UserORM.email) == email.lower())).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: int) -> UserORM | None:
    return db.get(UserORM, user_id)


def add_user(db: Session, user: UserORM) -> UserORM:
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def get_session_by_token_hash(db: Session, token_hash: str) -> UserSessionORM | None:
    query = select(UserSessionORM).where(UserSessionORM.token_hash == token_hash).with_for_update()
    return db.execute(query).scalar_one_or_none()


def delete_sessions_of_user(db: Session, user_id: int) -> None:
    db.execute(delete(UserSessionORM).where(UserSessionORM.user_id == user_id))


def delete_session(db: Session, session: UserSessionORM) -> None:
    db.delete(session)
    db.flush()


def add_session(db: Session, session: UserSessionORM) -> UserSessionORM:
    db.add(session)
    db.flush()
    return session
