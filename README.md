# Lab 1 – Etap 1.1: Products REST API

FastAPI + SQLAlchemy + Postgres (Docker), architektura warstwowa.

## Uruchomienie

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

docker compose up -d --build
uvicorn main:app --reload
```

Swagger: http://127.0.0.1:8000/docs

## Endpointy

- `GET /api/v1/products` – lista wszystkich produktów (z kategorią)
- `GET /api/v1/products/{id}` – produkt o danym ID (404, gdy nie istnieje)

## Baza

Tabele `categories` i `products` (klucz obcy `category_id`) tworzy `db/init/001_init.sql`.
Skrypt wykonuje się tylko przy pierwszym starcie z pustym wolumenem.
Reset bazy: `docker compose down -v` i ponownie `docker compose up -d --build`.

Podgląd danych:
`docker exec -it postgres_app psql -U appuser -d appdb -c "SELECT * FROM products;"`

## Warstwy

| Warstwa | Plik | Rola |
| --- | --- | --- |
| Web | `web/routes.py` | endpointy HTTP, kody statusu |
| Service | `service/product_service.py` | logika biznesowa |
| Data | `data/database.py`, `data/product_repository.py` | połączenie i zapytania |
| Model | `model/product_orm.py`, `model/product_schema.py` | tabele (ORM) i DTO (Pydantic) |
