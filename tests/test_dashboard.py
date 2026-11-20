from tests.test_basket import product, register_and_login, user  # noqa: F401  (fixtures)


def checkout(client, product_id, quantity=1) -> dict:
    client.post("/cart/items", json={"product_id": product_id, "quantity": quantity})
    return client.post("/cart/checkout").json()


def test_dashboard_requires_login(client):
    assert client.get("/bff/dashboard").status_code == 401


def test_dashboard_empty_user(client, user):
    data = client.get("/bff/dashboard").json()
    assert data["user"]["email"] == user
    assert data["orders"] == {"total": 0, "pending": 0, "completed": 0, "cancelled": 0, "completed_value": 0.0}
    assert data["cart"] == {"items": 0, "total": 0.0}
    assert data["recent_orders"] == [] and data["recent_cancelled"] == []


def test_dashboard_aggregates_orders_and_cart(client, user, product):
    p = product(quantity=20, price=100.0)
    done, cancelled, pending = (checkout(client, p["id"], q) for q in (2, 1, 1))
    client.post(f"/orders/{done['id']}/complete")
    client.post(f"/orders/{cancelled['id']}/cancel")
    client.post("/cart/items", json={"product_id": p["id"], "quantity": 3})

    data = client.get("/bff/dashboard").json()
    assert data["orders"] == {"total": 3, "pending": 1, "completed": 1, "cancelled": 1, "completed_value": 200.0}
    assert data["cart"] == {"items": 3, "total": 300.0}
    assert [o["id"] for o in data["recent_orders"]] == [pending["id"], cancelled["id"], done["id"]]
    assert [o["id"] for o in data["recent_cancelled"]] == [cancelled["id"]]


def test_cart_line_has_available_stock(client, user, product):
    p = product(quantity=7)
    cart = client.post("/cart/items", json={"product_id": p["id"], "quantity": 2}).json()
    assert cart["items"][0]["available"] == 7
