import uuid

import pytest

from app.REST.service import delivery

URL = "/api/v1/notifications"


@pytest.fixture
def sent(monkeypatch):
    """Replace real channels (MailHog/ntfy) with a recorder; tests stay offline."""
    calls = []
    monkeypatch.setitem(delivery.SENDERS, "EMAIL", calls.append)
    monkeypatch.setitem(delivery.SENDERS, "PUSH", calls.append)
    return calls


def payload(**overrides) -> dict:
    data = {
        "channel": "EMAIL",
        "recipient": "test@example.com",
        "subject": "Test",
        "message": "Hello",
        "scheduled_at": "2000-01-01T12:00:00+02:00",  # in the past = ready
    }
    data.update(overrides)
    return data


def test_post_returns_201_pending_and_time_in_utc(client):
    response = client.post(URL, json=payload())
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PENDING"
    assert body["scheduled_at"] in ("2000-01-01T10:00:00Z", "2000-01-01T10:00:00+00:00")


def test_get_list_and_by_id(client):
    created = client.post(URL, json=payload()).json()
    assert client.get(f"{URL}/{created['id']}").json() == created
    ids = [n["id"] for n in client.get(URL, params={"status": "PENDING"}).json()]
    assert created["id"] in ids
    assert client.get(f"{URL}/999999").status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"scheduled_at": "2030-01-01T10:00:00"},  # no time zone
        {"channel": "SMS"},
        {"message": ""},
        {"recipient": "not-an-email"},
        {"channel": "PUSH", "recipient": "bad topic!"},
    ],
)
def test_post_invalid_returns_422(client, overrides):
    assert client.post(URL, json=payload(**overrides)).status_code == 422


def test_send_now_delivers_and_second_call_is_409(client, sent):
    n = client.post(URL, json=payload(scheduled_at="2999-01-01T00:00:00Z")).json()
    response = client.post(f"{URL}/{n['id']}/send-now")
    assert response.status_code == 200
    assert response.json()["status"] == "SENT"
    assert response.json()["sent_at"] is not None
    assert [x.id for x in sent] == [n["id"]]
    assert client.post(f"{URL}/{n['id']}/send-now").status_code == 409
    assert client.post(f"{URL}/999999/send-now").status_code == 404


def test_send_now_failure_marks_failed(client, monkeypatch):
    def broken(_):
        raise ConnectionError("smtp down")

    monkeypatch.setitem(delivery.SENDERS, "EMAIL", broken)
    n = client.post(URL, json=payload()).json()
    body = client.post(f"{URL}/{n['id']}/send-now").json()
    assert body["status"] == "FAILED"
    assert body["last_error"] == "smtp down"
    assert body["attempts"] == 1


def test_cancel_then_send_now_is_409(client, sent):
    n = client.post(URL, json=payload()).json()
    assert client.post(f"{URL}/{n['id']}/cancel").json()["status"] == "CANCELLED"
    assert client.post(f"{URL}/{n['id']}/send-now").status_code == 409
    assert sent == []


def test_process_ready_sends_only_due_notifications(client, sent):
    due = client.post(URL, json=payload(channel="PUSH", recipient="ztp-test")).json()
    future = client.post(URL, json=payload(scheduled_at="2999-01-01T00:00:00Z")).json()

    response = client.post(f"{URL}/process-ready")
    assert response.status_code == 200
    assert response.json()["sent"] >= 1
    assert client.get(f"{URL}/{due['id']}").json()["status"] == "SENT"
    assert client.get(f"{URL}/{future['id']}").json()["status"] == "PENDING"
    assert future["id"] not in [x.id for x in sent]


def test_idempotency_key_returns_original(client):
    key = uuid.uuid4().hex
    first = client.post(URL, json=payload(idempotency_key=key))
    second = client.post(URL, json=payload(idempotency_key=key, message="other"))
    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["message"] == "Hello"


def test_metrics_prometheus_format(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# TYPE notifications_current gauge" in response.text
    assert 'notifications_current{status="PENDING",channel="EMAIL"}' in response.text


def test_separate_docs(client):
    products = client.get("/docs/products/openapi.json").json()["paths"]
    notifications = client.get("/docs/notifications/openapi.json").json()["paths"]
    assert all(p.startswith("/api/v1/products") for p in products)
    assert all(p.startswith("/api/v1/notifications") for p in notifications)
    assert client.get("/docs/notifications").status_code == 200
