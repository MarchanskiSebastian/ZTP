# ZTP – Products REST API (Lab 1) + Notifications (Projekt 2)

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\activate
pip install -r requirements.txt

docker compose down -v          # tylko przy zmianie schematu bazy
docker compose up -d --build    # postgres, mailhog, ntfy, prometheus
python -m uvicorn main:app --reload
python -m pytest -v             # testy (baza musi działać, kanały są mockowane)
```

| Adres | Co |
|---|---|
| http://127.0.0.1:8000/docs/products | Swagger – produkty |
| http://127.0.0.1:8000/docs/notifications | Swagger – powiadomienia |
| http://127.0.0.1:8000/metrics | metryki w formacie Prometheus |
| http://localhost:8025 | MailHog – skrzynka EMAIL |
| http://localhost:8080/ztp-demo | ntfy – temat PUSH z danych przykładowych |
| http://localhost:9090 | Prometheus (np. `notifications_current`, `notification_deliveries_total`) |

## Produkty
`GET/POST /api/v1/products`, `GET/PUT/DELETE /api/v1/products/{id}`, `GET /api/v1/products/{id}/history`.

## Powiadomienia
- `POST /api/v1/notifications` – `channel` (`EMAIL`/`PUSH`), `recipient` (e-mail lub temat ntfy), `subject`, `message`,
  `scheduled_at` (ISO 8601 **ze strefą**, zapisywany i zwracany w UTC; brak = teraz), `idempotency_key` (opcjonalny;
  powtórzony klucz zwraca oryginał z kodem 200 zamiast 201).
- `GET /api/v1/notifications[?status=…]`, `GET /api/v1/notifications/{id}`
- `POST /api/v1/notifications/{id}/send-now` – natychmiastowa wysyłka (tylko `PENDING`, inaczej 409)
- `POST /api/v1/notifications/{id}/cancel`
- `POST /api/v1/notifications/process-ready` – wysyła wszystkie `PENDING` z `scheduled_at <= now()`

Maszyna stanów: `PENDING → SENT | FAILED | CANCELLED`; stany końcowe nie mają przejść (próba = 409).

Worker w tle (start razem z aplikacją) co `WORKER_INTERVAL_SECONDS` (domyślnie 5) wywołuje to samo co `process-ready`;
`SELECT … FOR UPDATE SKIP LOCKED` chroni przed podwójną wysyłką. Wyłączenie: `WORKER_ENABLED=0`.
Dispatcher (`service/delivery.py`) wybiera kanał: EMAIL → SMTP MailHog, PUSH → HTTP POST do ntfy.

Dane przykładowe (`db/init/002_notifications.sql`) zawierają powiadomienia w każdym stanie oraz takie, które stają się
gotowe w ciągu 1, 2 i 5 minut – w Prometheusie widać, jak `PENDING` maleje, a `SENT` rośnie.
