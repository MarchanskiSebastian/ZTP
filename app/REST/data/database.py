import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = os.getenv("DB_NAME", "appdb")
DB_USER = os.getenv("DB_USER", "appuser")
DB_PASSWORD = os.getenv("DB_PASSWORD", "apppassword")

DATABASE_URL = (
    f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine = create_engine(DATABASE_URL, echo=False)


# Base class for all ORM models
class Base(DeclarativeBase):
    pass


SessionLocal = sessionmaker(bind=engine, autoflush=False)


# FastAPI dependency: one session per request, always closed
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
