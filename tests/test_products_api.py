def build_payload(name: str, **overrides) -> dict:
    payload = {"name": name, "price": 100.0, "quantity": 5, "category_id": 1}  # category 1: 10-600
    payload.update(overrides)
    return payload


def test_get_products_returns_200_and_list(client):
    response = client.get("/api/v1/products")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert {"id", "name", "price", "quantity", "category"} <= data[0].keys()


def test_get_missing_product_returns_404(client):
    assert client.get("/api/v1/products/999999").status_code == 404


def test_post_valid_product_returns_201(client, unique_name):
    response = client.post("/api/v1/products", json=build_payload(unique_name))
    assert response.status_code == 201
    created = response.json()
    assert created["name"] == unique_name
    assert created["quantity"] == 5
    assert created["category"]["id"] == 1
    assert client.get(f"/api/v1/products/{created['id']}").status_code == 200


def test_post_price_outside_category_range_returns_422(client, unique_name):
    response = client.post("/api/v1/products", json=build_payload(unique_name, price=9999.0))
    assert response.status_code == 422
    assert "przedziale" in response.json()["detail"]


def test_post_invalid_name_returns_422(client):
    assert client.post("/api/v1/products", json=build_payload("ab")).status_code == 422
    assert client.post("/api/v1/products", json=build_payload("bad name!")).status_code == 422


def test_post_forbidden_name_returns_422(client, unique_name):
    response = client.post("/api/v1/products", json=build_payload("admin" + unique_name[:5]))
    assert response.status_code == 422
    assert response.json()["detail"] == "Nazwa zawiera zakazaną frazę."


def test_post_negative_quantity_returns_422(client, unique_name):
    assert client.post("/api/v1/products", json=build_payload(unique_name, quantity=-1)).status_code == 422


def test_post_duplicate_name_returns_409(client, unique_name):
    assert client.post("/api/v1/products", json=build_payload(unique_name)).status_code == 201
    assert client.post("/api/v1/products", json=build_payload(unique_name)).status_code == 409


def test_post_unknown_category_returns_400(client, unique_name):
    assert client.post("/api/v1/products", json=build_payload(unique_name, category_id=999)).status_code == 400


def test_put_valid_change_returns_200(client, unique_name):
    product_id = client.post("/api/v1/products", json=build_payload(unique_name)).json()["id"]
    new = build_payload(unique_name, price=150.0, quantity=9)
    response = client.put(f"/api/v1/products/{product_id}", json=new)
    assert response.status_code == 200
    assert response.json()["price"] == 150.0
    assert response.json()["quantity"] == 9


def test_put_missing_product_returns_404(client, unique_name):
    assert client.put("/api/v1/products/999999", json=build_payload(unique_name)).status_code == 404


def test_history_records_create_and_replace(client, unique_name):
    product_id = client.post("/api/v1/products", json=build_payload(unique_name)).json()["id"]
    client.put(f"/api/v1/products/{product_id}", json=build_payload(unique_name, price=150.0))

    response = client.get(f"/api/v1/products/{product_id}/history")
    assert response.status_code == 200
    history = response.json()
    assert [h["action"] for h in history] == ["REPLACE", "CREATE"]  # newest first
    assert history[0]["previous_state"]["price"] == 100.0
    assert history[0]["current_state"]["price"] == 150.0
    assert history[1]["previous_state"] == {}
    assert history[1]["current_state"]["name"] == unique_name


def test_delete_returns_204_and_history_survives(client, unique_name):
    product_id = client.post("/api/v1/products", json=build_payload(unique_name)).json()["id"]
    response = client.delete(f"/api/v1/products/{product_id}")
    assert response.status_code == 204
    assert response.text == ""
    assert client.get(f"/api/v1/products/{product_id}").status_code == 404

    history = client.get(f"/api/v1/products/{product_id}/history").json()
    assert history[0]["action"] == "DELETE"
    assert history[0]["current_state"] == {}
    assert client.delete(f"/api/v1/products/{product_id}").status_code == 404


def test_history_of_unknown_product_returns_404(client):
    assert client.get("/api/v1/products/999999/history").status_code == 404
