# ZTP – Products REST API (Lab 1) + Notifications (Projekt 2) + Identity & Cart (Projekt 3)

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
| http://127.0.0.1:8000/identity-docs | Swagger – rejestracja, logowanie, sesja |
| http://127.0.0.1:8000/cart-docs | Swagger – koszyk i zamówienia |
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

## Identity (`app/identity`)
- `POST /auth/register` – e-mail + hasło (min. 8 znaków, litera i cyfra); hasło: PBKDF2-HMAC-SHA256, 600 000 iteracji, losowa sól 16 B.
- `POST /auth/login` – ustawia cookie `auth_token` (HttpOnly, SameSite=Lax). Nowe logowanie nadpisuje poprzednią sesję
  (jedna sesja na użytkownika), w bazie jest tylko SHA-256 tokenu.
- `GET /auth/me`, `POST /auth/logout`
- Sesja wygasa po `SESSION_TTL_MINUTES` (domyślnie 30) bezczynności; każde zapytanie z ważnym cookie ją przedłuża.

## Koszyk i zamówienia (`app/cart`)
- `GET /cart`, `POST /cart/items`, `PUT /cart/items/{product_id}`, `DELETE /cart/items/{product_id}` – ilość > 0 i nie większa niż stan magazynu.
- `POST /cart/checkout` – zamówienie `PENDING` z numerem `ZAM-YYYYMMDD-000001`, snapshot pozycji (nazwa, cena),
  zmniejszenie stanów magazynowych, wyczyszczenie koszyka.
- `GET /orders`, `GET /orders/{order_id}`, `POST /orders/{order_id}/complete`, `POST /orders/{order_id}/cancel`
- Maszyna stanów: `PENDING → COMPLETED | CANCELLED` (anulowanie zwraca towar na magazyn).
- Nagłówek `Idempotency-Key` (checkout/complete/cancel): powtórzony klucz zwraca pierwszy wynik (`Idempotent-Replayed: true`),
  klucz użyty dla innej operacji – 422. Wyniki są w tabeli `processed_commands`.
- Zakończenie zamówienia tworzy powiadomienia EMAIL (adres użytkownika) i PUSH (temat ntfy `ztp-user-<id>`), wysyła je worker.
- Zapis: Command Pattern (`commands.py` – komendy, handlery, `execute()`), odczyt: query service (`queries.py`) – CQRS.
