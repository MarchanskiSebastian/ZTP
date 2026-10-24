# Lab 1 – Products REST API (etapy 1.1–1.3)

```powershell
python -m venv venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\venv\Scripts\activate
pip install -r requirements.txt

docker compose down -v          # tylko przy zmianie schematu bazy
docker compose up -d --build
python -m uvicorn main:app --reload     # Swagger: http://127.0.0.1:8000/docs
python -m pytest -v                     # testy (baza musi działać)
```

Endpointy: `GET/POST /api/v1/products`, `GET/PUT/DELETE /api/v1/products/{id}`, `GET /api/v1/products/{id}/history`.
