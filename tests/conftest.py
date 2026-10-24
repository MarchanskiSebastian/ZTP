import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.REST.data.database import engine, get_db
from main import app


def _row_counts() -> tuple[int, int, int]:
    with engine.connect() as conn:
        return tuple(
            conn.execute(text(f"SELECT count(*) FROM {t}")).scalar_one()
            for t in ("products", "product_history", "categories")
        )


@pytest.fixture(scope="session", autouse=True)
def database_left_untouched():
    """Whole-session guard: row counts after all tests must equal the counts before."""
    before = _row_counts()
    yield
    assert _row_counts() == before, "Tests left traces in the database!"


@pytest.fixture(scope="function")
def db_session():
    """One test = one transaction on a dedicated connection, rolled back at the end."""
    connection = engine.connect()
    outer_transaction = connection.begin()
    # create_savepoint: commit() inside the app only releases a SAVEPOINT,
    # the outer transaction stays open and can still be rolled back
    session = Session(bind=connection, autoflush=False, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """TestClient whose endpoints use the test session instead of a fresh one."""

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def unique_name() -> str:
    """Unique product name: 11 letters/digits, passes the 3-20 alphanumeric rule."""
    return "T" + uuid.uuid4().hex[:10].upper()
