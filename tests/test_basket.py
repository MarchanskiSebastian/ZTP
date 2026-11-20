import hashlib
import re
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.REST.service import delivery
from main import app

PASSWORD = "Haslo1234"


def register_and_login(client, email=None) -> str:
    email = email or f"u{uuid.uuid4().hex[:10]}@example.com"
    assert client.post("/auth/register", json={"email": email, "password": PASSWORD}).status_code == 201
    assert client.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    return email


@pytest.fixture
def user(client) -> str:
    return register_and_login(client)


@pytest.fixture
def product(client):
    """Own product (stock 5, price 100.00) so tests do not depend on seed data."""
    def make(quantity=5, price=100.0):
        name = "B" + uuid.uuid4().hex[:10].upper()
        body = {"name": name, "price": price, "quantity": quantity, "category_id": 1}
        return client.post("/api/v1/products", json=body).json()
    return make


def stock(client, product_id) -> int:
    return client.get(f"/api/v1/products/{product_id}").json()["quantity"]


# ---------- identity ----------

def test_register_login_me_logout(client):
    email = f"u{uuid.uuid4().hex[:10]}@example.com"
    assert client.post("/auth/register", json={"email": email, "password": PASSWORD}).status_code == 201
    assert client.post("/auth/register", json={"email": email, "password": PASSWORD}).status_code == 409
    assert client.post("/auth/register", json={"email": "x" + email, "password": "short1"}).status_code == 422
    assert client.post("/auth/register", json={"email": "no-at-sign", "password": PASSWORD}).status_code == 422
    assert client.post("/auth/login", json={"email": email, "password": "Wrong1234"}).status_code == 401

    response = client.post("/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("auth_token=") and "HttpOnly" in cookie and "Max-Age=1800" in cookie
    assert client.get("/auth/me").json()["email"] == email

    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_password_stored_as_pbkdf2_with_salt(client, db_session):
    a, b = register_and_login(client), register_and_login(client)  # same password
    rows = db_session.execute(
        text("SELECT email, password_hash, password_salt, password_iterations FROM users WHERE email IN (:a, :b)"),
        {"a": a, "b": b},
    ).all()
    assert rows[0].password_salt != rows[1].password_salt
    assert rows[0].password_hash != rows[1].password_hash  # salt -> different hashes
    for row in rows:
        assert PASSWORD not in row.password_hash
        expected = hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), bytes.fromhex(row.password_salt),
                                       row.password_iterations).hex()
        assert row.password_hash == expected


def test_new_login_overwrites_previous_session(client, db_session):
    email = register_and_login(client)
    other = TestClient(app)  # second browser, same db session override
    assert other.post("/auth/login", json={"email": email, "password": PASSWORD}).status_code == 200
    assert other.get("/auth/me").status_code == 200
    assert client.get("/auth/me").status_code == 401  # old cookie no longer valid
    count = db_session.execute(text(
        "SELECT count(*) FROM user_sessions s JOIN users u ON u.id = s.user_id WHERE u.email = :e"
    ), {"e": email}).scalar_one()
    assert count == 1


def test_session_expires(client, user, db_session):
    db_session.execute(text("UPDATE user_sessions SET expires_at = now() - interval '1 second' "
                            "WHERE user_id = (SELECT id FROM users WHERE email = :e)"), {"e": user})
    response = client.get("/auth/me")
    assert response.status_code == 401
    assert "wygasła" in response.json()["detail"]


def test_session_is_extended_on_activity(client, user, db_session):
    db_session.execute(text("UPDATE user_sessions SET expires_at = now() + interval '1 minute' "
                            "WHERE user_id = (SELECT id FROM users WHERE email = :e)"), {"e": user})
    expires = datetime.fromisoformat(client.get("/auth/me").json()["session_expires_at"])
    assert expires > datetime.now(timezone.utc) + timedelta(minutes=29)


# ---------- cart ----------

def test_cart_requires_login(client):
    assert client.get("/cart").status_code == 401
    assert client.post("/cart/checkout").status_code == 401


def test_add_products_to_cart_with_validation(client, user, product):
    p = product(quantity=5)
    assert client.post("/cart/items", json={"product_id": p["id"], "quantity": 0}).status_code == 422
    assert client.post("/cart/items", json={"product_id": p["id"], "quantity": 6}).status_code == 409
    assert client.post("/cart/items", json={"product_id": 999999, "quantity": 1}).status_code == 404

    client.post("/cart/items", json={"product_id": p["id"], "quantity": 2})
    cart = client.post("/cart/items", json={"product_id": p["id"], "quantity": 2}).json()
    assert cart["items"][0]["quantity"] == 4 and cart["total"] == 400.0
    assert client.post("/cart/items", json={"product_id": p["id"], "quantity": 2}).status_code == 409  # 6 > 5

    assert client.put(f"/cart/items/{p['id']}", json={"quantity": 1}).json()["total"] == 100.0
    assert client.delete(f"/cart/items/{p['id']}").json() == {"items": [], "total": 0.0}


def test_checkout_empty_cart_is_422(client, user):
    assert client.post("/cart/checkout").status_code == 422


def test_checkout_creates_order_snapshot_updates_stock_and_clears_cart(client, user, product):
    p1, p2 = product(quantity=5, price=100.0), product(quantity=3, price=50.0)
    client.post("/cart/items", json={"product_id": p1["id"], "quantity": 2})
    client.post("/cart/items", json={"product_id": p2["id"], "quantity": 3})

    response = client.post("/cart/checkout", headers={"Idempotency-Key": uuid.uuid4().hex})
    assert response.status_code == 201
    order = response.json()
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    assert re.fullmatch(rf"ZAM-{today}-\d{{6}}", order["number"])
    assert order["status"] == "PENDING"
    assert order["total"] == 350.0
    assert [(i["product_name"], i["unit_price"], i["quantity"], i["line_total"]) for i in order["items"]] == [
        (p1["name"], 100.0, 2, 200.0), (p2["name"], 50.0, 3, 150.0)]

    assert stock(client, p1["id"]) == 3 and stock(client, p2["id"]) == 0
    assert client.get("/cart").json()["items"] == []

    # snapshot: changing the product later does not change the order
    client.put(f"/api/v1/products/{p1['id']}", json={"name": p1["name"], "price": 120.0, "quantity": 3, "category_id": 1})
    assert client.get(f"/orders/{order['id']}").json() == order
    assert order["id"] in [o["id"] for o in client.get("/orders").json()]


def test_order_numbers_are_sequential(client, user, product):
    numbers = []
    for _ in range(2):
        client.post("/cart/items", json={"product_id": product()["id"], "quantity": 1})
        numbers.append(client.post("/cart/checkout").json()["number"])
    assert int(numbers[1][-6:]) == int(numbers[0][-6:]) + 1


def test_checkout_idempotency_key(client, user, product):
    p = product(quantity=5)
    client.post("/cart/items", json={"product_id": p["id"], "quantity": 2})
    key = uuid.uuid4().hex
    first = client.post("/cart/checkout", headers={"Idempotency-Key": key})
    # cart is now empty; without idempotency this would be 422
    client.post("/cart/items", json={"product_id": p["id"], "quantity": 1})
    second = client.post("/cart/checkout", headers={"Idempotency-Key": key})
    assert second.json()["id"] == first.json()["id"]
    assert second.headers["Idempotent-Replayed"] == "true"
    assert len(client.get("/orders").json()) == 1
    assert stock(client, p["id"]) == 3  # stock reduced once


def test_orders_of_other_user_are_not_visible(client, user, product):
    client.post("/cart/items", json={"product_id": product()["id"], "quantity": 1})
    order_id = client.post("/cart/checkout").json()["id"]
    register_and_login(client)  # same client, now another user
    assert client.get(f"/orders/{order_id}").status_code == 404
    assert client.get("/orders").json() == []


# ---------- orders: state machine, idempotency, notifications ----------

@pytest.fixture
def pending_order(client, user, product):
    p = product(quantity=5)
    client.post("/cart/items", json={"product_id": p["id"], "quantity": 2})
    return client.post("/cart/checkout").json() | {"product_id": p["id"]}


def test_complete_order_status_and_idempotency(client, pending_order):
    url = f"/orders/{pending_order['id']}"
    key = uuid.uuid4().hex
    first = client.post(f"{url}/complete", headers={"Idempotency-Key": key})
    assert first.status_code == 200
    assert first.json()["status"] == "COMPLETED"
    assert first.json()["completed_at"] is not None

    replay = client.post(f"{url}/complete", headers={"Idempotency-Key": key})
    assert replay.status_code == 200
    assert replay.headers["Idempotent-Replayed"] == "true"
    assert replay.json() == first.json()

    # another key = a new attempt to complete an already completed order
    again = client.post(f"{url}/complete", headers={"Idempotency-Key": uuid.uuid4().hex})
    assert again.status_code == 409
    assert "COMPLETED -> COMPLETED" in again.json()["detail"]
    assert client.post(f"{url}/cancel").status_code == 409
    assert client.get(url).json()["status"] == "COMPLETED"


def test_idempotency_key_reused_for_other_operation_is_422(client, pending_order):
    key = uuid.uuid4().hex
    client.post(f"/orders/{pending_order['id']}/complete", headers={"Idempotency-Key": key})
    assert client.post("/cart/checkout", headers={"Idempotency-Key": key}).status_code == 422


def test_cancel_returns_stock(client, pending_order):
    assert stock(client, pending_order["product_id"]) == 3
    response = client.post(f"/orders/{pending_order['id']}/cancel")
    assert response.json()["status"] == "CANCELLED"
    assert stock(client, pending_order["product_id"]) == 5
    assert client.post(f"/orders/{pending_order['id']}/complete").status_code == 409


def test_completed_order_creates_email_and_push_once_and_worker_sends_them(client, user, pending_order,
                                                                           monkeypatch):
    sent = []
    monkeypatch.setitem(delivery.SENDERS, "EMAIL", sent.append)
    monkeypatch.setitem(delivery.SENDERS, "PUSH", sent.append)

    key = uuid.uuid4().hex
    client.post(f"/orders/{pending_order['id']}/complete", headers={"Idempotency-Key": key})
    client.post(f"/orders/{pending_order['id']}/complete", headers={"Idempotency-Key": key})  # replay
    client.post(f"/orders/{pending_order['id']}/complete", headers={"Idempotency-Key": "other"})  # 409

    mine = [n for n in client.get("/api/v1/notifications").json()
            if (n["idempotency_key"] or "").startswith(f"order-{pending_order['id']}-")]
    assert sorted((n["channel"], n["status"]) for n in mine) == [("EMAIL", "PENDING"), ("PUSH", "PENDING")]
    email = next(n for n in mine if n["channel"] == "EMAIL")
    assert email["recipient"] == user
    assert pending_order["number"] in email["subject"]

    client.post("/api/v1/notifications/process-ready")  # what the worker does every few seconds
    statuses = {n["id"]: n["status"] for n in client.get("/api/v1/notifications").json()}
    assert all(statuses[n["id"]] == "SENT" for n in mine)
    assert sorted(n.id for n in sent if n.id in {m["id"] for m in mine}) == sorted(m["id"] for m in mine)


def test_identity_and_cart_docs(client):
    identity = client.get("/identity-docs/openapi.json").json()["paths"]
    cart = client.get("/cart-docs/openapi.json").json()["paths"]
    assert set(identity) == {"/auth/register", "/auth/login", "/auth/me", "/auth/logout"}
    assert "/cart/checkout" in cart and "/orders/{order_id}" in cart and "/auth/login" not in cart
    assert client.get("/identity-docs").status_code == 200
    assert client.get("/cart-docs").status_code == 200
